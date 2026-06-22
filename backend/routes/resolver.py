from datetime import datetime, timedelta
import math
from db import get_connection
from routes.feasible import (
    fetch_distance, travel_time_secs, overlaps_availability,
    fetch_fuel_stations, fetch_location_has_fuel,
    fuel_needed, check_vehicle_fuel,
    INDIVIDUAL_SPEED_KMH, FUEL_FILL_TIME_MINS
)




# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fetch_plan_assigned_resources(plan_id, conflict_start, conflict_end, base_t0):
    """
    Find every vehicle and individual that is already occupied during the
    window [conflict_start, conflict_end) for a given plan.

    This is used to exclude busy resources when searching for replacements —
    we don't want to suggest a vehicle or crew member who is already assigned
    to another trip that overlaps the conflicting trip's time window.

    Parameters
    ----------
    plan_id        : int      – The plan whose trips we scan.
    conflict_start : datetime – Start of the conflicting trip's window.
    conflict_end   : datetime – End of the conflicting trip's window.
    base_t0        : datetime – Plan zero-point used to resolve offset times.

    Returns
    -------
    busy_vehicles    : set of vehicle_number strings
    busy_individuals : set of individual_id integers
    """
    conn = get_connection()
    cur  = conn.cursor()

    def to_secs(t):
        return t.hour * 3600 + t.minute * 60 + t.second

    # Check each trip in the plan and record vehicles whose window overlaps.
    cur.execute("""
        SELECT vehicle_number, start_offset, duration
        FROM trips WHERE plan_id = %s
    """, (plan_id,))
    rows = cur.fetchall()

    busy_vehicles = set()
    for vn, offset, dur in rows:
        trip_start = base_t0 + timedelta(seconds=to_secs(offset))
        trip_end   = trip_start + timedelta(seconds=to_secs(dur))
        # Standard interval overlap: [a,b) overlaps [c,d) iff a<d and b>c
        if trip_start < conflict_end and trip_end > conflict_start:
            busy_vehicles.add(vn)

    # Same overlap check for individuals via trip_crew join.
    cur.execute("""
        SELECT tc.individual_id, t.start_offset, t.duration
        FROM trip_crew tc
        JOIN trips t ON t.trip_id = tc.trip_id
        WHERE t.plan_id = %s
    """, (plan_id,))
    rows = cur.fetchall()

    busy_individuals = set()
    for iid, offset, dur in rows:
        trip_start = base_t0 + timedelta(seconds=to_secs(offset))
        trip_end   = trip_start + timedelta(seconds=to_secs(dur))
        if trip_start < conflict_end and trip_end > conflict_start:
            busy_individuals.add(iid)

    cur.close()
    conn.close()
    return busy_vehicles, busy_individuals


def fetch_same_type_vehicles(vehicle_number, exclude_numbers):
    """
    Fetch all vehicles of the same type as the given vehicle, excluding
    the original vehicle itself and any already-excluded numbers (busy or
    already assigned as replacements).

    Also loads each candidate's unavailability windows in a single batch
    query to avoid N+1 queries.

    Returns
    -------
    list[dict] – Each dict has vehicle details + avail_windows list.
    """
    conn = get_connection()
    cur  = conn.cursor()
    exclude_list = list(exclude_numbers) if exclude_numbers else ['__none__']

    # Subquery finds the vehicle_type_id of the original vehicle, then returns
    # all other vehicles of that same type that aren't excluded.
    cur.execute("""
        SELECT
            v.vehicle_number, v.vehicle_name, v.current_location_id,
            vt.default_speed, v.current_fuel_level,
            vt.fuel_capacity, vt.fuel_consumption_rate, vt.max_load_capacity
        FROM vehicles v
        JOIN vehicle_types vt ON vt.vehicle_type_id = v.vehicle_type_id
        WHERE vt.vehicle_type_id = (
            SELECT vt2.vehicle_type_id FROM vehicles v2
            JOIN vehicle_types vt2 ON vt2.vehicle_type_id = v2.vehicle_type_id
            WHERE v2.vehicle_number = %s
        )
        AND v.vehicle_number != %s
        AND v.vehicle_number != ALL(%s)
    """, (vehicle_number, vehicle_number, exclude_list))
    rows = cur.fetchall()

    if not rows:
        cur.close(); conn.close()
        return []

    # Batch-load availability windows for all candidate vehicles at once.
    cur.execute("""
        SELECT vehicle_number, not_available_from, not_available_to, reason
        FROM vehicle_availability WHERE vehicle_number = ANY(%s)
    """, ([r[0] for r in rows],))
    avail_rows = cur.fetchall()
    cur.close(); conn.close()

    # Build a lookup: vehicle_number → list of (not_from, not_to, reason) tuples.
    # Strip timezone info to keep comparisons naive throughout.
    avail_map = {}
    for r in avail_rows:
        avail_map.setdefault(r[0], []).append((
            r[1].replace(tzinfo=None) if hasattr(r[1], 'tzinfo') else r[1],
            r[2].replace(tzinfo=None) if hasattr(r[2], 'tzinfo') else r[2],
            r[3]
        ))

    return [{
        "vehicle_number": r[0], "vehicle_name": r[1],
        "current_location": r[2], "speed": float(r[3]),
        "current_fuel": float(r[4]), "fuel_capacity": float(r[5]),
        "fuel_consumption_rate": float(r[6]), "max_load_capacity": float(r[7]),
        "avail_windows": avail_map.get(r[0], [])
    } for r in rows]


def fetch_all_vehicles_except(exclude_numbers):
    """
    Fetch every vehicle in the fleet except those in exclude_numbers.

    Used when same-type replacement fails and we need to search the
    entire fleet (e.g. for combo or round-trip resolution strategies).

    Returns
    -------
    list[dict] – Same structure as fetch_same_type_vehicles().
    """
    conn = get_connection()
    cur  = conn.cursor()
    exclude_list = list(exclude_numbers) if exclude_numbers else ['__none__']

    cur.execute("""
        SELECT
            v.vehicle_number, v.vehicle_name, v.current_location_id,
            vt.default_speed, v.current_fuel_level,
            vt.fuel_capacity, vt.fuel_consumption_rate, vt.max_load_capacity
        FROM vehicles v
        JOIN vehicle_types vt ON vt.vehicle_type_id = v.vehicle_type_id
        WHERE v.vehicle_number != ALL(%s)
    """, (exclude_list,))
    rows = cur.fetchall()

    if not rows:
        cur.close(); conn.close()
        return []

    # Batch-load availability windows.
    cur.execute("""
        SELECT vehicle_number, not_available_from, not_available_to, reason
        FROM vehicle_availability WHERE vehicle_number = ANY(%s)
    """, ([r[0] for r in rows],))
    avail_rows = cur.fetchall()
    cur.close(); conn.close()

    avail_map = {}
    for r in avail_rows:
        avail_map.setdefault(r[0], []).append((
            r[1].replace(tzinfo=None) if hasattr(r[1], 'tzinfo') and r[1].tzinfo else r[1],
            r[2].replace(tzinfo=None) if hasattr(r[2], 'tzinfo') and r[2].tzinfo else r[2],
            r[3]
        ))

    return [{
        "vehicle_number": r[0], "vehicle_name": r[1],
        "current_location": r[2], "speed": float(r[3]),
        "current_fuel": float(r[4]), "fuel_capacity": float(r[5]),
        "fuel_consumption_rate": float(r[6]), "max_load_capacity": float(r[7]),
        "avail_windows": avail_map.get(r[0], [])
    } for r in rows]


def fetch_trip_actual_load(trip_id):
    """
    Calculate the total physical load weight for a trip:
        actual_load = quantity_of_load × weight_per_unit (from load_types table)

    Returns 0.0 if the trip has no load or the data is missing.
    Used to determine whether a replacement vehicle (or combo) has
    sufficient capacity to carry the original trip's cargo.
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT t.quantity_of_load, lt.weight
        FROM trips t
        JOIN load_types lt ON lt.load_type_id = t.load_type_id
        WHERE t.trip_id = %s
    """, (trip_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row or row[0] is None or row[1] is None:
        return 0.0
    return float(row[0]) * float(row[1])


def fetch_same_type_individuals(individual_id, exclude_ids):
    """
    Fetch all individuals of the same crew type as the given individual,
    excluding the original and any already-excluded IDs.

    Returns
    -------
    list[dict] – Each dict has individual details + avail_windows list.
    """
    conn = get_connection()
    cur  = conn.cursor()
    exclude_list = list(exclude_ids) if exclude_ids else [-1]

    # Subquery finds the crew_type_id of the original individual, then
    # returns all others of that type who aren't excluded.
    cur.execute("""
        SELECT i.individual_id, i.name, i.current_location_id, ct.crew_type_name
        FROM individuals i
        JOIN crew_types ct ON ct.crew_type_id = i.crew_type_id
        WHERE i.crew_type_id = (
            SELECT crew_type_id FROM individuals WHERE individual_id = %s
        )
        AND i.individual_id != %s
        AND i.individual_id != ALL(%s)
    """, (individual_id, individual_id, exclude_list))
    rows = cur.fetchall()

    if not rows:
        cur.close(); conn.close()
        return []

    # Batch-load availability windows for all candidates.
    cur.execute("""
        SELECT individual_id, not_available_from, not_available_to, reason
        FROM individual_availability WHERE individual_id = ANY(%s)
    """, ([r[0] for r in rows],))
    avail_rows = cur.fetchall()
    cur.close(); conn.close()

    avail_map = {}
    for r in avail_rows:
        avail_map.setdefault(r[0], []).append((
            r[1].replace(tzinfo=None) if hasattr(r[1], 'tzinfo') else r[1],
            r[2].replace(tzinfo=None) if hasattr(r[2], 'tzinfo') else r[2],
            r[3]
        ))

    return [{
        "individual_id": r[0], "name": r[1],
        "current_location": r[2], "crew_type": r[3],
        "avail_windows": avail_map.get(r[0], [])
    } for r in rows]


# ─────────────────────────────────────────────
# AVAILABILITY / REACHABILITY CHECKS
# ─────────────────────────────────────────────

def is_vehicle_available_reachable_fuelled(
    candidate, trip_start_loc, end_loc,
    actual_start, actual_end, base_t0
):
    """
    Gate check: returns True only if the candidate vehicle passes ALL three
    conditions needed to be a valid replacement:

    1. Availability  — not marked unavailable during [base_t0, actual_end).
    2. Fuel          — has enough fuel (or can refuel) to reach the trip start.
    3. Reachability  — can travel from its current location to trip_start_loc
                       in time, without its travel window hitting an unavailability.

    Uses base_t0 (not actual_start) as the window start so that the check
    covers any pre-trip travel/refuel time the vehicle needs.

    Returns False on any failure; True only if all three pass.
    """
    avail_windows    = candidate["avail_windows"]
    current_loc      = candidate["current_location"]
    speed            = candidate["speed"]
    current_fuel     = candidate["current_fuel"]
    fuel_capacity    = candidate["fuel_capacity"]
    consumption_rate = candidate["fuel_consumption_rate"]

    # ── Check 1: availability during the full trip window ──
    conflict, _ = overlaps_availability(base_t0, actual_end, avail_windows)
    if conflict:
        return False

    # ── Check 2: fuel (delegates to shared fuel check logic) ──
    fuel_conflict = check_vehicle_fuel(
        current_loc, trip_start_loc, end_loc,
        current_fuel, fuel_capacity, consumption_rate,
        speed, base_t0, actual_start, actual_end,
        candidate["vehicle_number"], avail_windows
    )
    if fuel_conflict:
        return False

    # ── Check 3: can the vehicle physically reach the start location? ──
    if current_loc == trip_start_loc:
        return True  # already there, no travel needed

    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None:
        return False  # no route exists
    if dist == 0:
        return True   # co-located

    # Work backwards: must depart by base_t0 minus travel time.
    travel_secs = travel_time_secs(dist, speed)
    depart_time = base_t0 - timedelta(seconds=travel_secs)
    conflict, _ = overlaps_availability(depart_time, base_t0, avail_windows)
    return not conflict


def is_individual_available_reachable(
    candidate, trip_start_loc, actual_start, actual_end, base_t0
):
    """
    Gate check for a crew member replacement: returns True only if:

    1. Availability  — not unavailable during [base_t0, actual_end).
    2. Reachability  — can travel from current location to trip_start_loc
                       in time (individuals have no fuel constraint).

    Returns False on any failure; True only if both pass.
    """
    avail_windows = candidate["avail_windows"]
    current_loc   = candidate["current_location"]

    # ── Check 1: availability ──
    conflict, _ = overlaps_availability(base_t0, actual_end, avail_windows)
    if conflict:
        return False

    # ── Check 2: reachability ──
    if current_loc == trip_start_loc:
        return True

    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None:
        return False
    if dist == 0:
        return True

    travel_secs = travel_time_secs(dist, INDIVIDUAL_SPEED_KMH)
    depart_time = base_t0 - timedelta(seconds=travel_secs)
    conflict, _ = overlaps_availability(depart_time, base_t0, avail_windows)
    return not conflict


# ─────────────────────────────────────────────
# FUEL COST (one-way, deadhead included)
# ─────────────────────────────────────────────

def compute_vehicle_fuel_cost(
    current_loc, start_loc, end_loc,
    current_fuel, fuel_capacity, consumption_rate, speed
):
    """
    Estimate the total fuel a candidate vehicle will consume to complete
    the trip, including the deadhead (positioning) leg from its current
    location to the trip's start location.

    The function also accounts for whether a refuel stop is needed:
    - If current fuel is sufficient (with a 100 km buffer) → just charge
      the full trip distance.
    - If at a fuel station already → charge full trip distance (refuel assumed).
    - If a detour to a station is needed → charge detour distance + trip distance.
    - If no reachable station exists → return infinity (infeasible).

    Returns
    -------
    float – Estimated fuel units consumed. float("inf") if infeasible.
    """
    dist_to_start  = fetch_distance(current_loc, start_loc) or 0.0
    dist_start_end = fetch_distance(start_loc, end_loc)     or 0.0
    fuel_to_start  = fuel_needed(dist_to_start, consumption_rate)
    # 100 km buffer ensures there's a safety margin after reaching the start.
    buffer_fuel    = fuel_needed(100.0, consumption_rate)
    total_dist     = dist_to_start + dist_start_end

    # ── Case 1: enough fuel including the safety buffer ──
    if current_fuel >= fuel_to_start + buffer_fuel:
        return fuel_needed(total_dist, consumption_rate)

    # ── Case 2: current location has a fuel station → refuel there ──
    if fetch_location_has_fuel(current_loc):
        return fuel_needed(total_dist, consumption_rate)

    # ── Case 3: must detour to a fuel station ──
    fuel_stations    = fetch_fuel_stations()
    best_detour_dist = float("inf")

    for station in fuel_stations:
        sid = station["location_id"]
        if sid == current_loc:
            continue

        dist_to_station    = fetch_distance(current_loc, sid)
        dist_station_start = fetch_distance(sid, start_loc)

        if dist_to_station is None or dist_station_start is None:
            continue
        # Can we reach the station on current fuel?
        if current_fuel < fuel_needed(dist_to_station, consumption_rate):
            continue
        # After filling up, can we reach start_loc (with buffer)?
        if fuel_capacity < (fuel_needed(dist_station_start, consumption_rate) + buffer_fuel):
            continue

        detour_dist = dist_to_station + dist_station_start
        if detour_dist < best_detour_dist:
            best_detour_dist = detour_dist

    if best_detour_dist == float("inf"):
        return float("inf")  # no viable station reachable

    # Charge: detour to station → start_loc → end_loc
    return fuel_needed(best_detour_dist + dist_start_end, consumption_rate)


# ─────────────────────────────────────────────
# ROUND-TRIP SCHEDULER
# ─────────────────────────────────────────────

def schedule_round_trips(
    vehicle,
    trip_start_loc,
    trip_end_loc,
    trip_duration_secs,   # DB duration for the forward leg (travel + unloading)
    total_load,
    first_round_start,
    avail_windows
):
    """
    Schedule one vehicle to make multiple round trips between trip_start_loc
    and trip_end_loc in order to carry a total load that exceeds its single
    capacity.

    Each round consists of:
      A. Optional refuel at (or near) start_loc if fuel is insufficient.
      B. Forward leg: depart start_loc → arrive end_loc (uses DB trip duration).
      C. Return leg: drive empty end_loc → start_loc (distance/speed calculation).

    The last round skips C (no need to return after final delivery).

    Parameters
    ----------
    vehicle            : dict   – Candidate vehicle dict (post deadhead fuel deduction).
    trip_start_loc     : int    – Location ID where each round departs from.
    trip_end_loc       : int    – Location ID where each round delivers to.
    trip_duration_secs : int    – Seconds for the forward leg (from DB).
    total_load         : float  – Total cargo weight to deliver.
    first_round_start  : datetime – Earliest the first round can begin.
    avail_windows      : list   – Vehicle unavailability windows.

    Returns
    -------
    list[dict] – One entry per round with depart/arrive times and refuel notes.
    None       – If any round cannot be scheduled (conflict or fuel failure).
    """
    speed            = vehicle["speed"]
    consumption_rate = vehicle["fuel_consumption_rate"]
    fuel_capacity    = vehicle["fuel_capacity"]
    max_load         = vehicle["max_load_capacity"]

    dist_forward = fetch_distance(trip_start_loc, trip_end_loc) or 0.0
    dist_return  = fetch_distance(trip_end_loc, trip_start_loc) or 0.0

    fuel_per_fwd = fuel_needed(dist_forward, consumption_rate)
    fuel_per_ret = fuel_needed(dist_return,  consumption_rate)

    # Return travel time is pure driving time (no unloading on the way back).
    return_travel_secs = travel_time_secs(dist_return, speed)
    fill_secs          = FUEL_FILL_TIME_MINS * 60

    # How many rounds are needed to move all the load?
    rounds_needed = math.ceil(total_load / max_load)
    current_fuel  = vehicle["current_fuel"]
    round_start   = first_round_start
    rounds        = []

    for round_num in range(1, rounds_needed + 1):
        # Remaining load for this round (last round may be a partial load).
        load_this_round = min(max_load, total_load - (round_num - 1) * max_load)
        is_last_round   = (round_num == rounds_needed)
        refuel_note     = None

        # ── Step A: refuel at start_loc if needed before departing ──
        # We only need enough fuel for the forward leg here; the return
        # leg fuel check is handled implicitly by the fuel carry-forward.
        if current_fuel < fuel_per_fwd:

            if fetch_location_has_fuel(trip_start_loc):
                # Station is right at the start location — no travel needed,
                # just the fill time.
                refuel_end = round_start + timedelta(seconds=fill_secs)
                conflict, _ = overlaps_availability(round_start, refuel_end, avail_windows)
                if conflict:
                    return None  # unavailable during refuel window

                round_start  = refuel_end   # departure shifts forward by fill time
                current_fuel = fuel_capacity
                refuel_note  = "Refuelled at start location before this round"

            else:
                # No station at start — find the nearest reachable station,
                # drive there and back, then continue with the round.
                fuel_stations    = fetch_fuel_stations()
                best_station     = None
                best_detour_secs = float("inf")

                for station in fuel_stations:
                    sid = station["location_id"]
                    if sid == trip_start_loc:
                        continue  # already handled above

                    dist_to_station   = fetch_distance(trip_start_loc, sid)
                    dist_station_back = fetch_distance(sid, trip_start_loc)

                    if dist_to_station is None or dist_station_back is None:
                        continue
                    # Must have enough fuel to reach the station.
                    if current_fuel < fuel_needed(dist_to_station, consumption_rate):
                        continue
                    # Full tank must cover the return leg from the station.
                    if fuel_capacity < fuel_needed(dist_station_back, consumption_rate):
                        continue

                    # Total detour: go to station + fill + come back to start_loc.
                    detour_secs = (
                        travel_time_secs(dist_to_station,   speed) +
                        fill_secs +
                        travel_time_secs(dist_station_back, speed)
                    )
                    if detour_secs < best_detour_secs:
                        best_detour_secs = detour_secs
                        best_station     = station

                if best_station is None:
                    return None  # no reachable station, round trip impossible

                detour_end = round_start + timedelta(seconds=best_detour_secs)
                conflict, _ = overlaps_availability(round_start, detour_end, avail_windows)
                if conflict:
                    return None  # unavailable during detour window

                round_start  = detour_end
                current_fuel = fuel_capacity
                refuel_note  = f"Refuelled at {best_station['location_name']} before this round"

            # Final safety check: even after refuelling, can the tank handle the forward leg?
            if fuel_capacity < fuel_per_fwd:
                return None

        # ── Step B: forward leg — depart start_loc, arrive end_loc ──
        # Uses the DB trip duration (includes travel + unloading time).
        depart_time = round_start
        arrive_time = depart_time + timedelta(seconds=trip_duration_secs)

        conflict, _ = overlaps_availability(depart_time, arrive_time, avail_windows)
        if conflict:
            return None  # unavailable during forward leg

        current_fuel -= fuel_per_fwd  # deduct fuel for forward leg

        rounds.append({
            "round":        round_num,
            "load":         load_this_round,
            "depart_start": depart_time.isoformat(),
            "arrive_end":   arrive_time.isoformat(),
            "refuel_note":  refuel_note,
        })

        # Last round: vehicle stays at end_loc, no return leg needed.
        if is_last_round:
            break

        # ── Step C: return leg — drive empty from end_loc back to start_loc ──
        # Return duration is calculated from distance/speed (not from DB)
        # since the return is an unladen repositioning leg, not a planned trip.
        return_depart = arrive_time
        return_arrive = return_depart + timedelta(seconds=return_travel_secs)

        conflict, _ = overlaps_availability(return_depart, return_arrive, avail_windows)
        if conflict:
            return None  # unavailable during return leg

        current_fuel = max(current_fuel - fuel_per_ret, 0.0)

        # Next round starts immediately once the vehicle is back at start_loc.
        round_start = return_arrive

    return rounds


def find_best_single_vehicle_round_trips(
    candidates, trip_start_loc, trip_end_loc,
    trip_duration_secs, total_load, actual_start, avail_windows_map
):
    """
    From a list of candidate vehicles, find the single best one to perform
    all necessary round trips to deliver the total load.

    "Best" is defined as: fewest rounds first, then lowest total fuel cost.

    For each candidate:
    - Compute deadhead travel time from current location to trip_start_loc.
    - Deduct deadhead fuel from current fuel.
    - Pass the adjusted state to schedule_round_trips().

    Parameters
    ----------
    candidates        : list[dict] – Pre-filtered available vehicles.
    trip_start_loc    : int        – Origin of each round.
    trip_end_loc      : int        – Destination of each round.
    trip_duration_secs: int        – Forward leg duration (from DB).
    total_load        : float      – Total cargo to deliver.
    actual_start      : datetime   – Earliest the first round may begin.
    avail_windows_map : dict       – vehicle_number → avail_windows list.

    Returns
    -------
    (best_vehicle, best_rounds, best_fuel) or (None, None, inf) if none work.
    """
    best_vehicle = None
    best_rounds  = None
    best_fuel    = float("inf")
    best_count   = float("inf")

    for v in candidates:
        # Calculate how long it takes to travel from current location to trip start.
        dist_dh = fetch_distance(v["current_location"], trip_start_loc) or 0.0
        dh_secs = travel_time_secs(dist_dh, v["speed"])
        fuel_dh = fuel_needed(dist_dh, v["fuel_consumption_rate"])

        # The vehicle can't start Round 1 until it has arrived at trip_start_loc.
        earliest_arrival = actual_start + timedelta(seconds=dh_secs) \
            if v["current_location"] != trip_start_loc else actual_start
        first_start = max(actual_start, earliest_arrival)

        avail = avail_windows_map.get(v["vehicle_number"], [])

        # Reduce current fuel by the deadhead cost before passing to scheduler.
        fuel_after_dh = max(v["current_fuel"] - fuel_dh, 0.0)
        v_copy = dict(v)
        v_copy["current_fuel"] = fuel_after_dh

        rounds = schedule_round_trips(
            v_copy, trip_start_loc, trip_end_loc,
            trip_duration_secs, total_load,
            first_start, avail
        )
        if rounds is None:
            continue  # this vehicle can't complete all rounds

        # Total fuel = deadhead + (forward legs × n_rounds) + (return legs × n_rounds-1)
        dist_fwd   = fetch_distance(trip_start_loc, trip_end_loc) or 0.0
        dist_ret   = fetch_distance(trip_end_loc, trip_start_loc) or 0.0
        n_rounds   = len(rounds)
        total_fuel = fuel_dh + fuel_needed(
            dist_fwd * n_rounds + dist_ret * (n_rounds - 1),
            v["fuel_consumption_rate"]
        )

        # Prefer fewer rounds first, then lower fuel.
        if (n_rounds, total_fuel) < (best_count, best_fuel):
            best_vehicle = v
            best_rounds  = rounds
            best_fuel    = total_fuel
            best_count   = n_rounds

    return best_vehicle, best_rounds, best_fuel


# ─────────────────────────────────────────────
# COMBO ROUND TRIPS (multi-vehicle, parallel)
# ─────────────────────────────────────────────

def find_best_combo_round_trips(
    candidates, trip_start_loc, trip_end_loc,
    trip_duration_secs, total_load, actual_start, avail_windows_map
):
    """
    Find the best combination of 2-3 vehicles that together can deliver the
    total load by running round trips IN PARALLEL — each vehicle handles its
    own share of the load simultaneously, not sequentially.

    This is preferred over a single vehicle doing many sequential round trips
    because parallel delivery is faster and spreads the wear across vehicles.

    Load split
    ----------
    Each vehicle's share is proportional to its max_load_capacity:
        share_v = total_load × (capacity_v / sum_of_all_capacities_in_combo)

    Each vehicle then independently runs schedule_round_trips() for its share.
    All vehicles start at actual_start (parallel, not sequential).

    Scoring
    -------
    A combo is valid only if ALL vehicles in it can complete their share.
    Among valid combos, prefer:
      1. Fewest total rounds across all vehicles (less time overall).
      2. Lowest total fuel cost as tiebreaker.

    Parameters
    ----------
    candidates        : list[dict] – Pre-filtered available+reachable+fuelled vehicles.
    trip_start_loc    : int        – Origin location for all rounds.
    trip_end_loc      : int        – Destination location for all rounds.
    trip_duration_secs: int        – Forward leg duration (from DB).
    total_load        : float      – Total cargo weight to deliver.
    actual_start      : datetime   – Earliest any vehicle can begin Round 1.
    avail_windows_map : dict       – vehicle_number → avail_windows list.

    Returns
    -------
    (best_combo_result, best_fuel) where best_combo_result is a list of dicts
    (one per vehicle with their rounds), or (None, inf) if no combo works.
    """
    from itertools import combinations

    dist_fwd = fetch_distance(trip_start_loc, trip_end_loc) or 0.0
    dist_ret = fetch_distance(trip_end_loc, trip_start_loc) or 0.0

    best_result     = None
    best_fuel       = float("inf")
    best_total_rds  = float("inf")

    for size in range(2, min(4, len(candidates) + 1)):
        for combo in combinations(candidates, size):
            total_capacity = sum(v["max_load_capacity"] for v in combo)

            # Split load proportionally to each vehicle's capacity.
            combo_result = []
            combo_fuel   = 0.0
            combo_rounds = 0
            valid        = True

            for v in combo:
                # This vehicle's share of the total load.
                share = total_load * (v["max_load_capacity"] / total_capacity)

                # Deadhead from current location to trip_start_loc.
                dist_dh   = fetch_distance(v["current_location"], trip_start_loc) or 0.0
                dh_secs   = travel_time_secs(dist_dh, v["speed"])
                fuel_dh   = fuel_needed(dist_dh, v["fuel_consumption_rate"])

                # First round can't start before the vehicle arrives.
                earliest_arrival = actual_start + timedelta(seconds=dh_secs) \
                    if v["current_location"] != trip_start_loc else actual_start
                first_start = max(actual_start, earliest_arrival)

                avail = avail_windows_map.get(v["vehicle_number"], [])

                # Deduct deadhead fuel before passing to the round-trip scheduler.
                fuel_after_dh = max(v["current_fuel"] - fuel_dh, 0.0)
                v_copy = dict(v)
                v_copy["current_fuel"] = fuel_after_dh

                rounds = schedule_round_trips(
                    v_copy, trip_start_loc, trip_end_loc,
                    trip_duration_secs, share,
                    first_start, avail
                )

                if rounds is None:
                    # This vehicle can't handle its share — whole combo fails.
                    valid = False
                    break

                n_rounds   = len(rounds)
                # Total fuel for this vehicle: deadhead + forward legs + return legs.
                total_fuel = fuel_dh + fuel_needed(
                    dist_fwd * n_rounds + dist_ret * (n_rounds - 1),
                    v["fuel_consumption_rate"]
                )

                combo_fuel   += total_fuel
                combo_rounds += n_rounds
                combo_result.append({
                    "vehicle_number": v["vehicle_number"],
                    "vehicle_name":   v["vehicle_name"],
                    "load_share":     round(share, 2),
                    "fuel_cost":      round(total_fuel, 2),
                    "rounds":         rounds,
                })

            if not valid:
                continue

            # Prefer fewer total rounds across all vehicles, then lower fuel.
            if (combo_rounds, combo_fuel) < (best_total_rds, best_fuel):
                best_total_rds = combo_rounds
                best_fuel      = combo_fuel
                best_result    = combo_result

    return best_result, best_fuel


# ─────────────────────────────────────────────
# COMBO (multi-vehicle, single pass)
# ─────────────────────────────────────────────

def find_optimal_vehicle_combo(
    original_vehicle_number, trip_id,
    trip_start_loc, trip_end_loc,
    actual_start, actual_end, base_t0,
    assigned_vehicles, used_replacements_vehicles
):
    """
    Find the smallest combination of available vehicles whose combined
    load capacity meets the trip's required capacity, minimising total
    fuel cost.

    This handles the case where no single vehicle can carry the full load
    but two or three smaller vehicles can together (load split).

    Strategy
    --------
    1. Fetch all non-excluded vehicles.
    2. Filter to those that pass the availability/reachability/fuel gate.
    3. Compute fuel cost for each candidate.
    4. Try all combinations of size 1 to 3 (cap to avoid combinatorial explosion).
    5. Return the combo with the smallest size and lowest fuel among those
       that meet the required capacity.

    Parameters
    ----------
    original_vehicle_number    : str  – The conflicting vehicle (for capacity lookup).
    trip_id                    : int  – Used to fetch actual load weight.
    assigned_vehicles          : set  – Vehicle numbers busy during the trip window.
    used_replacements_vehicles : set  – Already-assigned replacements in this run.

    Returns
    -------
    (combo, total_fuel) where combo is list[dict] or None if no solution found.
    """
    from itertools import combinations

    actual_load = fetch_trip_actual_load(trip_id)

    # Look up the original vehicle's type capacity to set the required capacity.
    # If there's actual cargo, required = min(actual_load, type_capacity).
    # If no cargo data, required = type_capacity (don't undersize the replacement).
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT vt.max_load_capacity FROM vehicles v
        JOIN vehicle_types vt ON vt.vehicle_type_id = v.vehicle_type_id
        WHERE v.vehicle_number = %s
    """, (original_vehicle_number,))
    row = cur.fetchone()
    cur.close(); conn.close()
    vehicle_type_capacity = float(row[0]) if row else 0.0

    required_capacity = min(actual_load, vehicle_type_capacity) if actual_load > 0 else vehicle_type_capacity
    exclude = assigned_vehicles | used_replacements_vehicles

    # Build pool of candidates that pass all gate checks.
    all_vehicles = fetch_all_vehicles_except(exclude)
    candidates = []
    for v in all_vehicles:
        if not is_vehicle_available_reachable_fuelled(
            v, trip_start_loc, trip_end_loc, actual_start, actual_end, base_t0
        ):
            continue
        fc = compute_vehicle_fuel_cost(
            v["current_location"], trip_start_loc, trip_end_loc,
            v["current_fuel"], v["fuel_capacity"],
            v["fuel_consumption_rate"], v["speed"]
        )
        if fc == float("inf"):
            continue  # infeasible fuel scenario
        v["fuel_cost"] = fc
        candidates.append(v)

    if not candidates:
        return None, float("inf")

    # Sort by fuel cost so combinations are evaluated cheapest-first.
    candidates.sort(key=lambda v: v["fuel_cost"])

    best_combo      = None
    best_fuel       = float("inf")
    best_combo_size = float("inf")

    # Try combos of size 1, 2, 3 — cap at 3 to avoid explosion with large fleets.
    for size in range(1, min(4, len(candidates) + 1)):
        for combo in combinations(candidates, size):
            # Combined capacity must meet or exceed what the original vehicle type carried.
            if sum(v["max_load_capacity"] for v in combo) < required_capacity:
                continue
            total_fuel = sum(v["fuel_cost"] for v in combo)
            # Prefer smaller combos (fewer vehicles); among equal sizes, prefer lower fuel.
            if size < best_combo_size or (size == best_combo_size and total_fuel < best_fuel):
                best_fuel       = total_fuel
                best_combo_size = size
                best_combo      = list(combo)

    return best_combo, best_fuel


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def resolve_conflicts(conflicts, plan_id, trip_map, base_t0):
    """
    Attempt to resolve every conflict detected by run_scheduler() by finding
    valid replacement resources.

    For each conflict the function tries multiple resolution strategies in
    priority order, using the first one that succeeds:

    Vehicle conflicts (tried in this order):
      1. Same-type single swap      – One vehicle of the same type.
      2. Multi-vehicle combo        – Multiple vehicles sharing the load.
      3. Single vehicle round trips – One vehicle making repeated trips.

    Individual conflicts:
      1. Same crew-type replacement – Nearest available person of the same type.

    The function tracks which replacements have been used across all conflicts
    in this call so the same resource is never double-assigned.

    Parameters
    ----------
    conflicts : list[dict] – Output of run_scheduler()["conflicts"].
    plan_id   : int        – The plan being resolved.
    trip_map  : dict       – trip_id → trip dict (from run_scheduler trip data).
    base_t0   : datetime   – Plan zero-point.

    Returns
    -------
    list[dict] – One resolution dict per conflict, with resolved=True/False
                 and replacement details.
    """
    # Track replacements assigned in this resolution run to avoid double-booking.
    used_replacements_vehicles    = set()
    used_replacements_individuals = set()
    resolutions = []

    # Pre-fetch availability windows for ALL vehicles once upfront,
    # so the round-trip scheduler can use them without hitting the DB repeatedly.
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT vehicle_number FROM vehicles")
    all_vnums = [r[0] for r in cur.fetchall()]
    avail_windows_map = {}
    for vn in all_vnums:
        cur.execute("""
            SELECT not_available_from, not_available_to, reason
            FROM vehicle_availability WHERE vehicle_number = %s
        """, (vn,))
        avail_windows_map[vn] = [
            (r[0].replace(tzinfo=None) if r[0].tzinfo else r[0],
             r[1].replace(tzinfo=None) if r[1].tzinfo else r[1],
             r[2])
            for r in cur.fetchall()
        ]
    cur.close(); conn.close()

    for conflict in conflicts:
        trip_id    = conflict["trip_id"]
        identifier = conflict["identifier"]   # vehicle number or individual name
        ctype      = conflict["conflict_type"]

        # Normalise actual_start/end to datetime objects (they may arrive as ISO strings).
        actual_start = conflict["actual_start"]
        actual_end   = conflict["actual_end"]
        if isinstance(actual_start, str):
            actual_start = datetime.fromisoformat(actual_start)
        if isinstance(actual_end, str):
            actual_end = datetime.fromisoformat(actual_end)

        trip = trip_map.get(trip_id)
        if not trip:
            # Trip data missing — cannot attempt any resolution.
            resolutions.append({
                "trip_id": trip_id, "original": identifier,
                "conflict_type": ctype, "replacement": None, "resolved": False
            })
            continue

        trip_start_loc = trip["start_location_id"]
        trip_end_loc   = trip.get("end_location_id")
        trip_dur_secs  = trip.get("duration_secs", 0)

        # Re-compute busy sets specifically for THIS conflict's time window,
        # so we don't exclude resources that are only busy at other times.
        assigned_vehicles, assigned_individuals = fetch_plan_assigned_resources(
            plan_id, actual_start, actual_end, base_t0
        )

        # ══════════════════════════════════════════
        # VEHICLE CONFLICT RESOLUTION
        # ══════════════════════════════════════════
        if ctype == "Vehicle":
            actual_load = fetch_trip_actual_load(trip_id)

            # ── Strategy 1: same-type single vehicle swap ──
            # Cheapest and simplest option: find one vehicle of the same type
            # that is available, reachable, and fuelled, then pick the lowest
            # fuel-cost one.
            same_type = fetch_same_type_vehicles(
                identifier, assigned_vehicles | used_replacements_vehicles
            )
            best      = None
            best_fuel = float("inf")

            for c in same_type:
                if not is_vehicle_available_reachable_fuelled(
                    c, trip_start_loc, trip_end_loc, actual_start, actual_end, base_t0
                ):
                    continue
                fc = compute_vehicle_fuel_cost(
                    c["current_location"], trip_start_loc, trip_end_loc,
                    c["current_fuel"], c["fuel_capacity"],
                    c["fuel_consumption_rate"], c["speed"]
                )
                if fc != float("inf") and fc < best_fuel:
                    best_fuel = fc
                    best      = c

            if best:
                # Found a same-type replacement — record and move to next conflict.
                used_replacements_vehicles.add(best["vehicle_number"])
                resolutions.append({
                    "trip_id":          trip_id,
                    "original":         identifier,
                    "conflict_type":    "Vehicle",
                    "replacement":      best["vehicle_number"],
                    "replacement_name": best["vehicle_name"],
                    "fuel_cost":        round(best_fuel, 2),
                    "resolved":         True,
                    "resolution_type":  "same_type_single",
                    "split":            False,
                    "rounds":           None,
                })
                continue  # ← skip to next conflict; this one is resolved

            # ── Strategy 2: multi-vehicle combo (single pass) ──
            # No single same-type vehicle worked. Try splitting the load
            # across multiple vehicles of any type in one simultaneous pass.
            combo, combo_fuel = find_optimal_vehicle_combo(
                identifier, trip_id,
                trip_start_loc, trip_end_loc,
                actual_start, actual_end, base_t0,
                assigned_vehicles, used_replacements_vehicles
            )

            # ── Strategy 3: multi-vehicle combo round trips (parallel) ──
            # Neither strategy 1 nor 2 worked (or combo capacity was insufficient).
            # Try 2-3 vehicles each doing round trips for their share of the load
            # simultaneously — faster than one vehicle doing all rounds sequentially.
            all_candidates = fetch_all_vehicles_except(
                assigned_vehicles | used_replacements_vehicles
            )
            rt_combo_candidates = [
                v for v in all_candidates
                if is_vehicle_available_reachable_fuelled(
                    v, trip_start_loc, trip_end_loc, actual_start, actual_end, base_t0
                )
            ]

            combo_rt_result, combo_rt_fuel = find_best_combo_round_trips(
                rt_combo_candidates, trip_start_loc, trip_end_loc,
                trip_dur_secs, actual_load, actual_start, avail_windows_map
            )

            # ── Strategy 4: single vehicle round trips ──
            # Last resort: one vehicle making all trips sequentially.
            rt_vehicle, rt_rounds, rt_fuel = find_best_single_vehicle_round_trips(
                rt_combo_candidates, trip_start_loc, trip_end_loc,
                trip_dur_secs, actual_load, actual_start, avail_windows_map
            )

            # ── Pick the best among combo, combo-round-trips, single-round-trips ──
            # Priority: fewer vehicles and parallel > sequential.
            # Among viable options, choose lowest total fuel cost.
            use_combo        = combo is not None
            use_combo_rt     = combo_rt_result is not None
            use_single_rt    = rt_vehicle is not None

            # Collect viable options and pick the cheapest.
            options = []
            if use_combo:     options.append(("combo",     combo_fuel))
            if use_combo_rt:  options.append(("combo_rt",  combo_rt_fuel))
            if use_single_rt: options.append(("single_rt", rt_fuel))

            best_option = min(options, key=lambda x: x[1]) if options else None

            if best_option and best_option[0] == "combo":
                for v in combo:
                    used_replacements_vehicles.add(v["vehicle_number"])
                resolutions.append({
                    "trip_id":          trip_id,
                    "original":         identifier,
                    "conflict_type":    "Vehicle",
                    "replacement":      [v["vehicle_number"] for v in combo],
                    "replacement_name": [v["vehicle_name"]   for v in combo],
                    "total_fuel_cost":  round(combo_fuel, 2),
                    "resolved":         True,
                    "resolution_type":  "multi_vehicle_combo",
                    "split":            len(combo) > 1,
                    "rounds":           None,
                })

            elif best_option and best_option[0] == "combo_rt":
                for v in combo_rt_result:
                    used_replacements_vehicles.add(v["vehicle_number"])
                resolutions.append({
                    "trip_id":          trip_id,
                    "original":         identifier,
                    "conflict_type":    "Vehicle",
                    "replacement":      [v["vehicle_number"] for v in combo_rt_result],
                    "replacement_name": [v["vehicle_name"]   for v in combo_rt_result],
                    "total_fuel_cost":  round(combo_rt_fuel, 2),
                    "resolved":         True,
                    "resolution_type":  "multi_vehicle_combo_round_trips",
                    "split":            True,
                    # Per-vehicle round schedules so the UI can show each vehicle's plan.
                    "rounds": {
                        v["vehicle_number"]: {
                            "load_share": v["load_share"],
                            "fuel_cost":  v["fuel_cost"],
                            "rounds":     v["rounds"],
                        }
                        for v in combo_rt_result
                    },
                })

            elif best_option and best_option[0] == "single_rt":
                used_replacements_vehicles.add(rt_vehicle["vehicle_number"])
                resolutions.append({
                    "trip_id":          trip_id,
                    "original":         identifier,
                    "conflict_type":    "Vehicle",
                    "replacement":      rt_vehicle["vehicle_number"],
                    "replacement_name": rt_vehicle["vehicle_name"],
                    "total_fuel_cost":  round(rt_fuel, 2),
                    "resolved":         True,
                    "resolution_type":  "single_vehicle_round_trips",
                    "split":            False,
                    "rounds": [
                        {
                            "round":        r["round"],
                            "load":         r["load"],
                            "depart_start": r["depart_start"],
                            "arrive_end":   r["arrive_end"],
                            "refuel_note":  r["refuel_note"],
                        }
                        for r in rt_rounds
                    ],
                })

            else:
                # All four strategies failed — unresolvable conflict.
                resolutions.append({
                    "trip_id":         trip_id,
                    "original":        identifier,
                    "conflict_type":   "Vehicle",
                    "replacement":     None,
                    "resolved":        False,
                    "resolution_type": "no_solution",
                    "rounds":          None,
                })

        # ══════════════════════════════════════════
        # INDIVIDUAL CONFLICT RESOLUTION
        # ══════════════════════════════════════════
        elif ctype == "Individual":
            # Look up the individual_id from the trip's crew list using the name.
            # (identifier is the name string for individuals, not an ID.)
            individual_id = next(
                (c["individual_id"] for c in trip["crew"] if c["name"] == identifier),
                None
            )
            if individual_id is None:
                # Crew member not found in trip data — cannot resolve.
                resolutions.append({
                    "trip_id": trip_id, "original": identifier,
                    "conflict_type": "Individual", "replacement": None, "resolved": False
                })
                continue

            # Fetch all same-type crew members who aren't busy or already assigned.
            candidates = fetch_same_type_individuals(
                individual_id,
                assigned_individuals | used_replacements_individuals
            )
            best      = None
            best_dist = float("inf")

            for c in candidates:
                if not is_individual_available_reachable(
                    c, trip_start_loc, actual_start, actual_end, base_t0
                ):
                    continue
                # Among valid candidates, prefer the one closest to the trip start
                # (minimises travel time / disruption).
                dist = fetch_distance(c["current_location"], trip_start_loc) or 0.0
                if dist < best_dist:
                    best_dist = dist
                    best      = c

            if best:
                used_replacements_individuals.add(best["individual_id"])
                resolutions.append({
                    "trip_id":          trip_id,
                    "original":         identifier,
                    "conflict_type":    "Individual",
                    "replacement":      best["name"],
                    "replacement_name": best["name"],
                    "crew_type":        best["crew_type"],
                    "resolved":         True,
                })
            else:
                # No same-type crew member available — unresolvable.
                resolutions.append({
                    "trip_id": trip_id, "original": identifier,
                    "conflict_type": "Individual", "replacement": None, "resolved": False
                })

    return resolutions
