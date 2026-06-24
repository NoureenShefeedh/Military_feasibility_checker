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
# PRIORITY HELPERS
# ─────────────────────────────────────────────

# Maps priority strings to numeric ranks so they can be compared with < / >.
# Higher number = higher priority.
PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def parse_plan_name_from_reason(reason):
    """
    Extract the plan name from a reason string of the form:
        "Assigned to <Plan Name>"

    Returns the plan name string, or None if the reason doesn't match
    the expected format.
    """
    # No reason text at all -> nothing to parse.
    if not reason:
        return None
    prefix = "Assigned to "
    # Only treat it as a "plan assignment" reason if it starts with the expected prefix.
    if reason.startswith(prefix):
        # Strip the prefix and any stray whitespace to get just the plan name.
        return reason[len(prefix):].strip()
    return None


def fetch_plan_priority(plan_name):
    """
    Look up the priority of a plan by its name.

    Returns the priority string ('low', 'medium', 'high') or None if
    the plan is not found.
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT priority FROM plans WHERE plan_name = %s",
        (plan_name,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    # Convert to str in case the DB driver returns something else (e.g. an Enum).
    return str(row[0]) if row else None


def fetch_current_plan_priority(plan_id):
    """
    Look up the priority of the current plan by its ID.

    Returns the priority string ('low', 'medium', 'high') or None.
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT priority FROM plans WHERE plan_id = %s",
        (plan_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return str(row[0]) if row else None


def is_poachable_from_lower_priority(reason, not_available_from, current_plan_priority):
    """
    Determine whether a resource blocked by an 'Assigned to <Plan>' reason
    can be poached because:

    1. The reason string matches the "Assigned to <Plan Name>" format.
    2. The blocking plan's priority is STRICTLY lower than the current plan.
    3. The blocking assignment has not yet started (not_available_from > now).

    Parameters
    ----------
    reason                 : str      – The unavailability reason string.
    not_available_from     : datetime – When the blocking assignment starts.
    current_plan_priority  : str      – Priority of the plan being resolved.

    Returns
    -------
    (poachable: bool, blocking_plan_name: str or None)
    """
    # Step 1: confirm this unavailability is actually caused by another plan assignment.
    plan_name = parse_plan_name_from_reason(reason)
    if not plan_name:
        return False, None

    # Step 2: find out how important that other ("blocking") plan is.
    blocking_priority = fetch_plan_priority(plan_name)
    if not blocking_priority:
        # Couldn't find the blocking plan in the DB -> be safe and don't poach.
        return False, None

    # Convert both priorities to numeric ranks for comparison.
    # Unknown priority strings default to -1 (lowest possible), keeping comparisons safe.
    current_rank  = PRIORITY_ORDER.get(current_plan_priority, -1)
    blocking_rank = PRIORITY_ORDER.get(blocking_priority, -1)

    if current_rank <= blocking_rank:
        # Current plan is not strictly higher priority — cannot poach.
        return False, None

    # Step 3: only allow poaching if the blocking assignment hasn't started yet.
    # (We don't want to rip a resource away from a trip that's already underway.)
    now = datetime.now()
    naf = not_available_from.replace(tzinfo=None) if not_available_from.tzinfo else not_available_from
    if naf <= now:
        # Already started — cannot poach.
        return False, None

    return True, plan_name


def check_vehicle_poachable(
    vehicle_number, conflict_avail_windows, current_plan_priority,
    conflict_start, conflict_end
):
    """
    Check whether the conflicting vehicle itself is poachable — i.e. the
    SPECIFIC unavailability window that is actually causing THIS conflict
    (the one overlapping [conflict_start, conflict_end)) is an assignment
    to a lower-priority plan that hasn't started yet.

    IMPORTANT: a vehicle can have many unrelated unavailability windows
    (e.g. "Maintenance" right now, and a completely separate future
    "Assigned to <Plan>" window weeks later). We must only look at the
    window that actually overlaps the current conflict's time range —
    otherwise an unrelated future assignment could incorrectly be reported
    as the reason this vehicle is "poachable", even though it has nothing
    to do with why the trip is conflicting right now.

    Parameters
    ----------
    vehicle_number          : str       – The vehicle in conflict.
    conflict_avail_windows  : list       – All (not_from, not_to, reason) windows for this vehicle.
    current_plan_priority   : str        – Priority of the plan being resolved.
    conflict_start          : datetime   – Start of the window causing THIS conflict (actual_start).
    conflict_end            : datetime   – End of the window causing THIS conflict (actual_end).

    Returns
    -------
    (poachable: bool, blocking_plan_name: str or None)
    """
    for not_from, not_to, reason in conflict_avail_windows:
        # Skip windows that don't actually overlap the time range causing
        # this specific conflict — they're unrelated to why this trip failed.
        if not (not_from < conflict_end and not_to > conflict_start):
            continue
        poachable, plan_name = is_poachable_from_lower_priority(
            reason, not_from, current_plan_priority
        )
        if poachable:
            return True, plan_name
    return False, None


def check_individual_poachable(individual_name, trip_crew, current_plan_priority, conflict_start, conflict_end):
    """
    Check whether the conflicting individual is poachable from a lower-priority
    plan.

    Looks up the individual's availability windows and checks ONLY the
    window that actually overlaps [conflict_start, conflict_end) — i.e. the
    one actually causing this specific conflict — for a lower-priority plan
    assignment that hasn't started. Unrelated windows (a different reason,
    or a different time period entirely) are ignored, so an unconnected
    future "Assigned to <Plan>" record can't be mistaken for the reason
    this person is unavailable right now.

    Returns
    -------
    (poachable: bool, blocking_plan_name: str or None, individual_id: int or None)
    """
    # Find the individual_id from the crew list (we only have the name here).
    individual_id = next(
        (c["individual_id"] for c in trip_crew if c["name"] == individual_name),
        None
    )
    if individual_id is None:
        # Can't find this person in the crew list — nothing to poach.
        return False, None, None

    # Pull every unavailability record for this individual from the DB.
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT not_available_from, not_available_to, reason
        FROM individual_availability WHERE individual_id = %s
    """, (individual_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Check only the window(s) that actually overlap THIS conflict's window.
    for not_from, not_to, reason in rows:
        # Normalize to naive datetime (strip timezone) before comparing.
        nf = not_from.replace(tzinfo=None) if not_from.tzinfo else not_from
        nt = not_to.replace(tzinfo=None) if not_to.tzinfo else not_to
        if not (nf < conflict_end and nt > conflict_start):
            # This window has nothing to do with why the person is
            # unavailable for THIS trip — skip it.
            continue
        poachable, plan_name = is_poachable_from_lower_priority(
            reason, nf, current_plan_priority
        )
        if poachable:
            return True, plan_name, individual_id

    return False, None, individual_id


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

    # Helper: convert a TIME value (offset/duration) into total seconds,
    # so it can be added to base_t0 as a timedelta.
    def to_secs(t):
        return t.hour * 3600 + t.minute * 60 + t.second

    # ---- Find vehicles already busy on another trip within this plan ----
    cur.execute("""
        SELECT vehicle_number, start_offset, duration
        FROM trips WHERE plan_id = %s
    """, (plan_id,))
    rows = cur.fetchall()

    busy_vehicles = set()
    for vn, offset, dur in rows:
        # Reconstruct each trip's actual start/end time from the plan's base_t0
        # plus its stored offset/duration.
        trip_start = base_t0 + timedelta(seconds=to_secs(offset))
        trip_end   = trip_start + timedelta(seconds=to_secs(dur))
        # Standard interval-overlap check: trips overlap if one starts before
        # the other ends, in both directions.
        if trip_start < conflict_end and trip_end > conflict_start:
            busy_vehicles.add(vn)

    # ---- Find individuals already busy on another trip within this plan ----
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
    # Postgres "= ALL(%s)" needs a non-empty array; substitute a dummy value
    # if there's nothing to exclude.
    exclude_list = list(exclude_numbers) if exclude_numbers else ['__none__']

    # Find all vehicles that share the SAME vehicle_type_id as the original
    # vehicle, excluding the original itself and anything already excluded.
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

    # Batch-fetch availability windows for ALL candidates at once (avoids N+1 queries).
    cur.execute("""
        SELECT vehicle_number, not_available_from, not_available_to, reason
        FROM vehicle_availability WHERE vehicle_number = ANY(%s)
    """, ([r[0] for r in rows],))
    avail_rows = cur.fetchall()
    cur.close(); conn.close()

    # Group availability rows by vehicle_number into a lookup dict.
    avail_map = {}
    for r in avail_rows:
        avail_map.setdefault(r[0], []).append((
            r[1].replace(tzinfo=None) if hasattr(r[1], 'tzinfo') else r[1],
            r[2].replace(tzinfo=None) if hasattr(r[2], 'tzinfo') else r[2],
            r[3]
        ))

    # Build the final list of candidate dicts, attaching each vehicle's
    # availability windows from the lookup dict above.
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

    # No vehicle_type filtering here — we want the WHOLE fleet (minus exclusions).
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
    # Guard against missing trip/load-type data or NULL quantity/weight.
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
    # Use an out-of-range dummy ID (-1) when there's nothing to exclude.
    exclude_list = list(exclude_ids) if exclude_ids else [-1]

    # Find individuals with the SAME crew_type_id as the original individual.
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

    # Batch-fetch availability for all candidates at once.
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

    1. Availability  — not marked unavailable during [actual_start, actual_end).
    2. Fuel          — has enough fuel (or can refuel) to reach the trip start.
    3. Reachability  — can travel from its current location to trip_start_loc
                       in time, without its travel window hitting an unavailability.

    All checks are anchored on actual_start (this trip's own real start
    time), not base_t0 (the plan's zero-point) — we only care whether the
    vehicle can be in place and free for THIS trip, not for the whole plan.
    """
    avail_windows    = candidate["avail_windows"]
    current_loc      = candidate["current_location"]
    speed            = candidate["speed"]
    current_fuel     = candidate["current_fuel"]
    fuel_capacity    = candidate["fuel_capacity"]
    consumption_rate = candidate["fuel_consumption_rate"]

    # --- Condition 1: Availability ---
    # The candidate must be free for the trip's own actual window —
    # actual_start (this trip's real start) through actual_end (trip finish).
    conflict, _ = overlaps_availability(actual_start, actual_end, avail_windows)
    if conflict:
        return False

    # --- Condition 2: Fuel ---
    # Delegate to the shared fuel-check helper (handles direct-fuel,
    # on-site refuel, and detour-to-station cases).
    fuel_conflict = check_vehicle_fuel(
        current_loc, trip_start_loc, end_loc,
        current_fuel, fuel_capacity, consumption_rate,
        speed, actual_start, actual_start, actual_end,
        candidate["vehicle_number"], avail_windows
    )
    if fuel_conflict:
        return False

    # --- Condition 3: Reachability ---
    # If the vehicle is already at the trip's start location, no travel is needed.
    if current_loc == trip_start_loc:
        return True

    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None:
        # No known route between these locations -> can't reach the trip.
        return False
    if dist == 0:
        return True

    # Work out how long the trip to "get there" would take, then check that
    # the vehicle isn't unavailable during that travel window.
    # Anchored on actual_start (not base_t0) — we only care whether the
    # vehicle can physically reach the trip in time for THIS trip's own
    # start, not the plan's overall zero-point.
    travel_secs = travel_time_secs(dist, speed)
    depart_time = actual_start - timedelta(seconds=travel_secs)
    conflict, _ = overlaps_availability(depart_time, actual_start, avail_windows)
    return not conflict


def is_individual_available_reachable(
    candidate, trip_start_loc, actual_start, actual_end, base_t0
):
    """
    Gate check for a crew member replacement: returns True only if:

    1. Availability  — not unavailable during [actual_start, actual_end).
    2. Reachability  — can travel from current location to trip_start_loc in time.

    Both checks are anchored on actual_start (this trip's own real start
    time), not base_t0 (the plan's zero-point).
    """
    avail_windows = candidate["avail_windows"]
    current_loc   = candidate["current_location"]

    # --- Condition 1: Availability ---
    conflict, _ = overlaps_availability(actual_start, actual_end, avail_windows)
    if conflict:
        return False

    # --- Condition 2: Reachability ---
    if current_loc == trip_start_loc:
        return True

    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None:
        return False
    if dist == 0:
        return True

    # Individuals travel at a fixed walking/commute speed (not vehicle speed).
    # Anchored on actual_start (not base_t0) — same reasoning as the vehicle check.
    travel_secs = travel_time_secs(dist, INDIVIDUAL_SPEED_KMH)
    depart_time = actual_start - timedelta(seconds=travel_secs)
    conflict, _ = overlaps_availability(depart_time, actual_start, avail_windows)
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
    the trip, including the deadhead leg from its current location to
    the trip's start location.
    """
    # "Deadhead" leg: travelling empty from current location to the trip start.
    dist_to_start  = fetch_distance(current_loc, start_loc) or 0.0
    # The actual trip leg itself, start -> end.
    dist_start_end = fetch_distance(start_loc, end_loc)     or 0.0
    fuel_to_start  = fuel_needed(dist_to_start, consumption_rate)
    # Safety buffer: require enough fuel for an extra 100km beyond what's
    # strictly needed, so the vehicle isn't left stranded with zero margin.
    buffer_fuel    = fuel_needed(100.0, consumption_rate)
    total_dist     = dist_to_start + dist_start_end

    # Case A: vehicle already has enough fuel (plus buffer) to reach the
    # start point without needing to refuel at all.
    if current_fuel >= fuel_to_start + buffer_fuel:
        return fuel_needed(total_dist, consumption_rate)

    # Case B: not enough fuel, but there's a fuel station right at the
    # vehicle's current location — it can simply top up before departing.
    if fetch_location_has_fuel(current_loc):
        return fuel_needed(total_dist, consumption_rate)

    # Case C: no fuel on-site — search for the best detour to a fuel station
    # along the way that the vehicle can actually reach and refuel at.
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
        # Vehicle must have enough fuel to reach the station in the first place.
        if current_fuel < fuel_needed(dist_to_station, consumption_rate):
            continue
        # After refuelling to full capacity, it must have enough to reach the
        # trip start with the safety buffer intact.
        if fuel_capacity < (fuel_needed(dist_station_start, consumption_rate) + buffer_fuel):
            continue

        detour_dist = dist_to_station + dist_station_start
        if detour_dist < best_detour_dist:
            best_detour_dist = detour_dist

    if best_detour_dist == float("inf"):
        # No viable fuel station found within reach.
        return float("inf")

    # Total fuel = detour to/through the station + the actual trip leg.
    return fuel_needed(best_detour_dist + dist_start_end, consumption_rate)


# ─────────────────────────────────────────────
# ROUND-TRIP SCHEDULER
# ─────────────────────────────────────────────

def schedule_round_trips(
    vehicle,
    trip_start_loc,
    trip_end_loc,
    trip_duration_secs,
    total_load,
    first_round_start,
    avail_windows
):
    """
    Schedule one vehicle to make multiple round trips between trip_start_loc
    and trip_end_loc in order to carry a total load that exceeds its single
    capacity.
    """
    speed            = vehicle["speed"]
    consumption_rate = vehicle["fuel_consumption_rate"]
    fuel_capacity    = vehicle["fuel_capacity"]
    max_load         = vehicle["max_load_capacity"]

    # Forward leg (start -> end) and return leg (end -> start) distances.
    dist_forward = fetch_distance(trip_start_loc, trip_end_loc) or 0.0
    dist_return  = fetch_distance(trip_end_loc, trip_start_loc) or 0.0

    fuel_per_fwd = fuel_needed(dist_forward, consumption_rate)
    fuel_per_ret = fuel_needed(dist_return,  consumption_rate)

    return_travel_secs = travel_time_secs(dist_return, speed)
    fill_secs          = FUEL_FILL_TIME_MINS * 60

    # How many round trips are needed to move the entire load, given the
    # vehicle's max capacity per trip.
    rounds_needed = math.ceil(total_load / max_load)
    current_fuel  = vehicle["current_fuel"]
    round_start   = first_round_start
    rounds        = []

    for round_num in range(1, rounds_needed + 1):
        # How much load this particular round carries (last round may be partial).
        load_this_round = min(max_load, total_load - (round_num - 1) * max_load)
        is_last_round   = (round_num == rounds_needed)
        refuel_note     = None

        # --- Refuel check before departing on this round, if needed ---
        if current_fuel < fuel_per_fwd:

            if fetch_location_has_fuel(trip_start_loc):
                # Refuel right where we are (the trip's start location).
                refuel_end = round_start + timedelta(seconds=fill_secs)
                conflict, _ = overlaps_availability(round_start, refuel_end, avail_windows)
                if conflict:
                    # Vehicle becomes unavailable during the refuel window -> bail out entirely.
                    return None

                round_start  = refuel_end
                current_fuel = fuel_capacity
                refuel_note  = "Refuelled at start location before this round"

            else:
                # No fuel at the start location — search for the best detour
                # to a nearby station (go there, fill up, come back) before
                # starting this round.
                fuel_stations    = fetch_fuel_stations()
                best_station     = None
                best_detour_secs = float("inf")

                for station in fuel_stations:
                    sid = station["location_id"]
                    if sid == trip_start_loc:
                        continue

                    dist_to_station   = fetch_distance(trip_start_loc, sid)
                    dist_station_back = fetch_distance(sid, trip_start_loc)

                    if dist_to_station is None or dist_station_back is None:
                        continue
                    if current_fuel < fuel_needed(dist_to_station, consumption_rate):
                        continue
                    if fuel_capacity < fuel_needed(dist_station_back, consumption_rate):
                        continue

                    detour_secs = (
                        travel_time_secs(dist_to_station,   speed) +
                        fill_secs +
                        travel_time_secs(dist_station_back, speed)
                    )
                    if detour_secs < best_detour_secs:
                        best_detour_secs = detour_secs
                        best_station     = station

                if best_station is None:
                    # No reachable station can save this round -> the whole
                    # round-trip plan fails.
                    return None

                detour_end = round_start + timedelta(seconds=best_detour_secs)
                conflict, _ = overlaps_availability(round_start, detour_end, avail_windows)
                if conflict:
                    return None

                round_start  = detour_end
                current_fuel = fuel_capacity
                refuel_note  = f"Refuelled at {best_station['location_name']} before this round"

            # Even after refuelling to full capacity, if the tank still can't
            # cover the forward leg, this vehicle simply can't do the job.
            if fuel_capacity < fuel_per_fwd:
                return None

        # --- Depart on the forward leg of this round ---
        depart_time = round_start
        arrive_time = depart_time + timedelta(seconds=trip_duration_secs)

        conflict, _ = overlaps_availability(depart_time, arrive_time, avail_windows)
        if conflict:
            return None

        current_fuel -= fuel_per_fwd

        rounds.append({
            "round":        round_num,
            "load":         load_this_round,
            "depart_start": depart_time.isoformat(),
            "arrive_end":   arrive_time.isoformat(),
            "refuel_note":  refuel_note,
        })

        if is_last_round:
            # No need to schedule a return leg after the final round.
            break

        # --- Return leg back to the start location for the next round ---
        return_depart = arrive_time
        return_arrive = return_depart + timedelta(seconds=return_travel_secs)

        conflict, _ = overlaps_availability(return_depart, return_arrive, avail_windows)
        if conflict:
            return None

        current_fuel = max(current_fuel - fuel_per_ret, 0.0)
        round_start  = return_arrive

    return rounds


def find_best_single_vehicle_round_trips(
    candidates, trip_start_loc, trip_end_loc,
    trip_duration_secs, total_load, actual_start, avail_windows_map
):
    """
    From a list of candidate vehicles, find the single best one to perform
    all necessary round trips to deliver the total load.

    "Best" is defined as: fewest rounds first, then lowest total fuel cost.
    """
    best_vehicle = None
    best_rounds  = None
    best_fuel    = float("inf")
    best_count   = float("inf")

    for v in candidates:
        # Work out the "deadhead" leg: how long/how much fuel it costs the
        # vehicle to travel from its current location to the trip's start.
        dist_dh = fetch_distance(v["current_location"], trip_start_loc) or 0.0
        dh_secs = travel_time_secs(dist_dh, v["speed"])
        fuel_dh = fuel_needed(dist_dh, v["fuel_consumption_rate"])

        # The vehicle can't start its first round until it physically arrives
        # at the trip's start location (unless it's already there).
        earliest_arrival = actual_start + timedelta(seconds=dh_secs) \
            if v["current_location"] != trip_start_loc else actual_start
        first_start = max(actual_start, earliest_arrival)

        avail = avail_windows_map.get(v["vehicle_number"], [])

        # Account for fuel burned during the deadhead leg before simulating rounds.
        fuel_after_dh = max(v["current_fuel"] - fuel_dh, 0.0)
        v_copy = dict(v)
        v_copy["current_fuel"] = fuel_after_dh

        rounds = schedule_round_trips(
            v_copy, trip_start_loc, trip_end_loc,
            trip_duration_secs, total_load,
            first_start, avail
        )
        if rounds is None:
            # This vehicle can't complete the job at all -> skip it.
            continue

        # Compute total fuel used: deadhead + all forward/return legs across rounds.
        dist_fwd   = fetch_distance(trip_start_loc, trip_end_loc) or 0.0
        dist_ret   = fetch_distance(trip_end_loc, trip_start_loc) or 0.0
        n_rounds   = len(rounds)
        total_fuel = fuel_dh + fuel_needed(
            dist_fwd * n_rounds + dist_ret * (n_rounds - 1),
            v["fuel_consumption_rate"]
        )

        # Prefer fewer rounds; break ties by lower fuel cost (tuple comparison).
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
    total load by running round trips IN PARALLEL.
    """
    from itertools import combinations

    dist_fwd = fetch_distance(trip_start_loc, trip_end_loc) or 0.0
    dist_ret = fetch_distance(trip_end_loc, trip_start_loc) or 0.0

    best_result    = None
    best_fuel      = float("inf")
    best_total_rds = float("inf")

    # Try combos of size 2 and 3 (size 1 is handled by the single-vehicle strategy).
    for size in range(2, min(4, len(candidates) + 1)):
        for combo in combinations(candidates, size):
            # Total load capacity available across this combo of vehicles.
            total_capacity = sum(v["max_load_capacity"] for v in combo)

            combo_result = []
            combo_fuel   = 0.0
            combo_rounds = 0
            valid        = True

            for v in combo:
                # Split the total load proportionally to each vehicle's capacity.
                share = total_load * (v["max_load_capacity"] / total_capacity)

                dist_dh   = fetch_distance(v["current_location"], trip_start_loc) or 0.0
                dh_secs   = travel_time_secs(dist_dh, v["speed"])
                fuel_dh   = fuel_needed(dist_dh, v["fuel_consumption_rate"])

                earliest_arrival = actual_start + timedelta(seconds=dh_secs) \
                    if v["current_location"] != trip_start_loc else actual_start
                first_start = max(actual_start, earliest_arrival)

                avail = avail_windows_map.get(v["vehicle_number"], [])

                fuel_after_dh = max(v["current_fuel"] - fuel_dh, 0.0)
                v_copy = dict(v)
                v_copy["current_fuel"] = fuel_after_dh

                # Simulate this vehicle's own round trips for its share of the load.
                rounds = schedule_round_trips(
                    v_copy, trip_start_loc, trip_end_loc,
                    trip_duration_secs, share,
                    first_start, avail
                )

                if rounds is None:
                    # If ANY vehicle in the combo can't do its share, the
                    # whole combo is invalid.
                    valid = False
                    break

                n_rounds   = len(rounds)
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

            # Prefer the combo with fewer total rounds (across all vehicles),
            # then the lowest total fuel cost.
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
    """
    from itertools import combinations

    actual_load = fetch_trip_actual_load(trip_id)

    # Look up the ORIGINAL vehicle's type capacity, used as a fallback/cap
    # for how much capacity we actually need to replace.
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

    # Required capacity is the smaller of the actual load weight and the
    # original vehicle's rated capacity (don't over-provision beyond what
    # the original vehicle was meant to carry).
    required_capacity = min(actual_load, vehicle_type_capacity) if actual_load > 0 else vehicle_type_capacity
    exclude = assigned_vehicles | used_replacements_vehicles

    # Pull the whole fleet (minus exclusions) and filter down to only
    # vehicles that pass the availability/fuel/reachability gate check.
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
            # Vehicle can't get fuelled up at all -> not a viable candidate.
            continue
        v["fuel_cost"] = fc
        candidates.append(v)

    if not candidates:
        return None, float("inf")

    # Sort cheapest-fuel-first as a minor optimisation (doesn't change
    # correctness, just makes the combo search slightly more predictable).
    candidates.sort(key=lambda v: v["fuel_cost"])

    best_combo      = None
    best_fuel       = float("inf")
    best_combo_size = float("inf")

    # Try combos of increasing size (1 up to 3 vehicles) until we find ones
    # whose combined capacity covers the requirement, picking the smallest
    # combo size first, then lowest fuel cost as a tiebreaker.
    for size in range(1, min(4, len(candidates) + 1)):
        for combo in combinations(candidates, size):
            if sum(v["max_load_capacity"] for v in combo) < required_capacity:
                continue
            total_fuel = sum(v["fuel_cost"] for v in combo)
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
      0. Poach same vehicle from lower-priority plan  ← NEW
      1. Same-type single swap
      2. Multi-vehicle combo
      3. Combo round trips (parallel)
      4. Single vehicle round trips

    Individual conflicts (tried in this order):
      0. Poach same individual from lower-priority plan  ← NEW
      1. Same crew-type replacement
    """
    # Track which replacement resources we've already handed out during this
    # resolution pass, so the same vehicle/individual isn't double-booked
    # across two different conflicts.
    used_replacements_vehicles    = set()
    used_replacements_individuals = set()
    resolutions = []

    # Fetch current plan's priority once upfront — used for all poach checks.
    current_plan_priority = fetch_current_plan_priority(plan_id)

    # Pre-fetch availability windows for ALL vehicles once upfront, to avoid
    # repeated per-vehicle queries later (used by the round-trip strategies).
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

    # ── Main loop: process each detected conflict one at a time ──
    for conflict in conflicts:
        trip_id    = conflict["trip_id"]
        identifier = conflict["identifier"]
        ctype      = conflict["conflict_type"]
        subtype    = conflict.get("conflict_subtype", "")

        actual_start = conflict["actual_start"]
        actual_end   = conflict["actual_end"]
        # Conflicts may arrive with datetimes serialized as ISO strings
        # (e.g. from a JSON payload) — normalize them back to datetime objects.
        if isinstance(actual_start, str):
            actual_start = datetime.fromisoformat(actual_start)
        if isinstance(actual_end, str):
            actual_end = datetime.fromisoformat(actual_end)

        trip = trip_map.get(trip_id)
        if not trip:
            # Trip data missing entirely -> can't resolve, record as failed.
            resolutions.append({
                "trip_id": trip_id, "original": identifier,
                "conflict_type": ctype, "replacement": None, "resolved": False
            })
            continue

        trip_start_loc = trip["start_location_id"]
        trip_end_loc   = trip.get("end_location_id")
        trip_dur_secs  = trip.get("duration_secs", 0)

        # Find out which vehicles/individuals are already busy elsewhere in
        # this plan during the conflict window, so we don't suggest them.
        assigned_vehicles, assigned_individuals = fetch_plan_assigned_resources(
            plan_id, actual_start, actual_end, base_t0
        )

        # ══════════════════════════════════════════
        # VEHICLE CONFLICT RESOLUTION
        # ══════════════════════════════════════════
        if ctype == "Vehicle":
            actual_load = fetch_trip_actual_load(trip_id)

            # ── Strategy 0: poach the same vehicle from a lower-priority plan ──
            # Only applies when the conflict subtype is 'unavailable' and the
            # blocking reason is an assignment to a plan of strictly lower priority
            # whose window hasn't started yet.
            if subtype == "unavailable" and current_plan_priority:
                vehicle_avail_windows = avail_windows_map.get(identifier, [])
                poachable, blocking_plan = check_vehicle_poachable(
                    identifier, vehicle_avail_windows, current_plan_priority,
                    actual_start, actual_end
                )
                if poachable:
                    # Resolved without needing any new vehicle — we just
                    # reassign the SAME vehicle, overriding the lower-priority plan.
                    resolutions.append({
                        "trip_id":            trip_id,
                        "original":           identifier,
                        "conflict_type":      "Vehicle",
                        "replacement":        identifier,
                        "replacement_name":   identifier,
                        "resolved":           True,
                        "resolution_type":    "poached_from_lower_priority_plan",
                        "poached_from_plan":  blocking_plan,
                        "note":               f"Taken from lower priority plan: {blocking_plan}",
                        "split":              False,
                        "rounds":             None,
                        "fuel_cost":          None,
                    })
                    used_replacements_vehicles.add(identifier)
                    continue  # resolved — skip all other strategies

            # ── Strategy 1: same-type single vehicle swap ──
            same_type = fetch_same_type_vehicles(
                identifier, assigned_vehicles | used_replacements_vehicles
            )
            best      = None
            best_fuel = float("inf")

            # Among same-type candidates that pass the gate check, pick the
            # one with the lowest total fuel cost.
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
                # Found a clean single-vehicle same-type swap -> done, move on.
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
                continue

            # No same-type swap worked — fall through to more complex strategies.

            # ── Strategy 2: multi-vehicle combo (single pass) ──
            combo, combo_fuel = find_optimal_vehicle_combo(
                identifier, trip_id,
                trip_start_loc, trip_end_loc,
                actual_start, actual_end, base_t0,
                assigned_vehicles, used_replacements_vehicles
            )

            # ── Strategy 3: multi-vehicle combo round trips (parallel) ──
            # Gather candidates that pass the gate check once, and reuse them
            # for both the combo-round-trip and single-vehicle-round-trip strategies.
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
            rt_vehicle, rt_rounds, rt_fuel = find_best_single_vehicle_round_trips(
                rt_combo_candidates, trip_start_loc, trip_end_loc,
                trip_dur_secs, actual_load, actual_start, avail_windows_map
            )

            # ── Pick the best among remaining strategies ──
            # Collect whichever of strategies 2-4 actually produced a result,
            # then choose the cheapest (lowest fuel cost) one overall.
            options = []
            if combo is not None:         options.append(("combo",     combo_fuel))
            if combo_rt_result is not None: options.append(("combo_rt", combo_rt_fuel))
            if rt_vehicle is not None:    options.append(("single_rt", rt_fuel))

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
                # Every strategy failed — leave the conflict unresolved.
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
            # Look up the conflicting individual's ID from the trip's crew list.
            individual_id = next(
                (c["individual_id"] for c in trip["crew"] if c["name"] == identifier),
                None
            )

            # ── Strategy 0: poach the same individual from a lower-priority plan ──
            # Only applies when the conflict subtype is 'unavailable'.
            if subtype == "unavailable" and current_plan_priority:
                poachable, blocking_plan, ind_id = check_individual_poachable(
                    identifier, trip["crew"], current_plan_priority,
                    actual_start, actual_end
                )
                if poachable:
                    if ind_id:
                        used_replacements_individuals.add(ind_id)
                    resolutions.append({
                        "trip_id":           trip_id,
                        "original":          identifier,
                        "conflict_type":     "Individual",
                        "replacement":       identifier,
                        "replacement_name":  identifier,
                        "resolved":          True,
                        "resolution_type":   "poached_from_lower_priority_plan",
                        "poached_from_plan": blocking_plan,
                        "note":              f"Taken from lower priority plan: {blocking_plan}",
                    })
                    continue  # resolved — skip standard replacement search

            # ── Strategy 1: same crew-type replacement ──
            if individual_id is None:
                # Couldn't even identify who the conflicting person is -> can't resolve.
                resolutions.append({
                    "trip_id": trip_id, "original": identifier,
                    "conflict_type": "Individual", "replacement": None, "resolved": False
                })
                continue

            candidates = fetch_same_type_individuals(
                individual_id,
                assigned_individuals | used_replacements_individuals
            )
            best      = None
            best_dist = float("inf")

            # Among same-crew-type candidates that pass the gate check,
            # prefer whoever is physically closest to the trip's start location.
            for c in candidates:
                if not is_individual_available_reachable(
                    c, trip_start_loc, actual_start, actual_end, base_t0
                ):
                    continue
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
                # No viable replacement found -> leave unresolved.
                resolutions.append({
                    "trip_id": trip_id, "original": identifier,
                    "conflict_type": "Individual", "replacement": None, "resolved": False
                })

    return resolutions