from datetime import datetime, timedelta
from db import get_connection

 
# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

# Speed (km/h) assumed for crew members travelling on foot / by personal transport
# to reach a trip's start location.
INDIVIDUAL_SPEED_KMH = 40.0

# Time (minutes) assumed for a vehicle to complete a fuel fill-up stop.
FUEL_FILL_TIME_MINS  = 10


# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────
# Load all trips belonging to *plan_id* for a given date, together with
# every trip's route, vehicle, and crew details.


def fetch_plan_data(plan_id, date_str, time_str):
    conn = get_connection()
    cur  = conn.cursor()


    # Retrieve the plan's default start time so we can fall back to it
    # when the caller has not provided an explicit override.
    cur.execute("SELECT default_start_time FROM plans WHERE plan_id = %s", (plan_id,))
    row           = cur.fetchone()
    default_start = row[0]

    # Decide which time to use as the plan's BASE_T0.
    if time_str:
        t0_time = datetime.strptime(time_str, "%H:%M").time()
    else:
        t0_time = default_start

    base_date = datetime.strptime(date_str, "%Y-%m-%d")
    base_t0   = datetime.combine(base_date, t0_time)

    # Fetch every trip for this plan, joining in route, vehicle, and vehicle-type
    # data so we have everything needed for conflict detection in a single query.
    cur.execute("""
        SELECT
            t.trip_id,
            t.vehicle_number,
            t.start_offset,
            t.duration,
            r.start_location_id,
            r.end_location_id,
            vt.default_speed,
            v.current_location_id,
            v.current_fuel_level,
            vt.fuel_consumption_rate,
            vt.fuel_capacity
        FROM trips t
        JOIN routes        r  ON r.route_id          = t.route_id
        JOIN vehicles      v  ON v.vehicle_number     = t.vehicle_number
        JOIN vehicle_types vt ON vt.vehicle_type_id   = v.vehicle_type_id
        WHERE t.plan_id = %s
        ORDER BY t.start_offset
    """, (plan_id,))
    trip_rows = cur.fetchall()

    trips = []
    for row in trip_rows:
        trip_id = row[0]

        # For each trip, also load the assigned crew members.
        cur.execute("""
            SELECT i.individual_id, i.current_location_id, i.name
            FROM trip_crew tc
            JOIN individuals i ON i.individual_id = tc.individual_id
            WHERE tc.trip_id = %s
        """, (trip_id,))
        crew = cur.fetchall()


        # Convert a time object to total seconds 
        def time_to_secs(t):
            return t.hour * 3600 + t.minute * 60 + t.second

        trips.append({
            "trip_id":               row[0],
            "vehicle_number":        row[1],
            "start_offset_secs":     time_to_secs(row[2]),
            "duration_secs":         time_to_secs(row[3]),
            "start_location_id":     row[4],
            "end_location_id":       row[5],
            "vehicle_speed":         float(row[6]),
            "vehicle_current_loc":   row[7],
            "current_fuel":          float(row[8]),
            "fuel_consumption_rate": float(row[9]),
            "fuel_capacity":         float(row[10]),
            "crew": [
                {"individual_id": c[0], "current_location_id": c[1], "name": c[2]}
                for c in crew
            ],
        })

    cur.close()
    conn.close()
    return base_t0, trips

#Get distance between two locations using location IDs. Returns None if no route exists.
def fetch_distance(from_loc, to_loc):
    #returns 0.0 if from_loc and to_loc are the same
    if from_loc == to_loc:
        return 0.0
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT distance FROM routes
        WHERE start_location_id = %s AND end_location_id = %s
        LIMIT 1
    """, (from_loc, to_loc))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return float(row[0]) if row else None

#Return every location that has a fuel station available.
def fetch_fuel_stations():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT location_id, location_name
        FROM locations
        WHERE has_fuel_station = TRUE
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"location_id": r[0], "location_name": r[1]} for r in rows]

#Load all unavailability windows for every vehicle and individual that
#appears in the given plan.
def fetch_availability(plan_id):
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT DISTINCT t.vehicle_number
        FROM trips t WHERE t.plan_id = %s
    """, (plan_id,))
    vehicle_numbers = [r[0] for r in cur.fetchall()]

    cur.execute("""
        SELECT DISTINCT tc.individual_id
        FROM trip_crew tc
        JOIN trips t ON t.trip_id = tc.trip_id
        WHERE t.plan_id = %s
    """, (plan_id,))
    individual_ids = [r[0] for r in cur.fetchall()]

    vehicle_avail = {}
    for vn in vehicle_numbers:
        cur.execute("""
            SELECT not_available_from, not_available_to, reason
            FROM vehicle_availability WHERE vehicle_number = %s
        """, (vn,))
        vehicle_avail[vn] = [(r[0], r[1], r[2]) for r in cur.fetchall()]

    individual_avail = {}
    for ind_id in individual_ids:
        cur.execute("""
            SELECT not_available_from, not_available_to, reason
            FROM individual_availability WHERE individual_id = %s
        """, (ind_id,))
        individual_avail[ind_id] = [(r[0], r[1], r[2]) for r in cur.fetchall()]

    cur.close()
    conn.close()
    return vehicle_avail, individual_avail

#Check whether a specific location has a fuel station.
def fetch_location_has_fuel(location_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT has_fuel_station FROM locations WHERE location_id = %s",
        (location_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return bool(row[0]) if row else False


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

#Convert a distance and speed into a travel duration in seconds.
def travel_time_secs(distance_km, speed_kmh):
    if distance_km is None or distance_km == 0:
        return 0.0
    return (distance_km / speed_kmh) * 3600.0

#Convert a distance and fuel consumption rate into the amount of fuel needed.
def fuel_needed(distance_km, consumption_rate):
    if distance_km is None or distance_km == 0:
        return 0.0
    return distance_km * consumption_rate

#Test whether the interval [start_dt, end_dt) overlaps any unavailability
#window in *avail_windows*
def overlaps_availability(start_dt, end_dt, avail_windows):
    for not_from, not_to, reason in avail_windows:
        nf = not_from.replace(tzinfo=None) if not_from.tzinfo is not None else not_from
        nt = not_to.replace(tzinfo=None)   if not_to.tzinfo   is not None else not_to
        if start_dt < nt and end_dt > nf:
            return True, (nf, nt, reason)
    return False, None


# ─────────────────────────────────────────────
# CONFLICT MAKERS
# ─────────────────────────────────────────────
#Build a conflict dict for a resource that is explicitly marked
#unavailable during the trip window.   The 'earliest_available' field tells callers the soonest they could
   # reschedule, which equals the end of the unavailability window.
def make_unavailable_conflict(trip_id, identifier, conflict_type, window, actual_start, actual_end):
    return {
        "trip_id":            trip_id,
        "identifier":         identifier,
        "conflict_type":      conflict_type,
        "conflict_subtype":   "unavailable",
        "reason":             window[2],
        "not_available_from": window[0].isoformat(),
        "not_available_to":   window[1].isoformat(),
        "earliest_available": window[1].isoformat(),
        "actual_start":       actual_start.isoformat() if hasattr(actual_start, 'isoformat') else str(actual_start),
        "actual_end":         actual_end.isoformat()   if hasattr(actual_end,   'isoformat') else str(actual_end),
    }

 #Build a conflict dict for a vehicle that cannot reach the trip's start
  # location due to insufficient fuel, and cannot be refuelled in time
def make_fuel_conflict(trip_id, identifier, conflict_type, reason, actual_start, actual_end):
    return {
        "trip_id":            trip_id,
        "identifier":         identifier,
        "conflict_type":      conflict_type,
        "conflict_subtype":   "fuel",
        "reason":             reason,
        "not_available_from": None,
        "not_available_to":   None,
        "earliest_available": None,
        "actual_start":       actual_start.isoformat() if hasattr(actual_start, 'isoformat') else str(actual_start),
        "actual_end":         actual_end.isoformat()   if hasattr(actual_end,   'isoformat') else str(actual_end),
    }

#Build a conflict dict for the case where a vehicle *could* refuel
    #(a station exists and is reachable) but the detour to refuel would
    #fall within an unavailability window, making it impossible to refuel
    #and still arrive at the trip start on time.
def make_fuel_stop_late_conflict(trip_id, identifier, conflict_type, reason, actual_start, actual_end):
    return {
        "trip_id":            trip_id,
        "identifier":         identifier,
        "conflict_type":      conflict_type,
        "conflict_subtype":   "fuel_stop_late",
        "reason":             reason,
        "not_available_from": None,
        "not_available_to":   None,
        "earliest_available": None,
        "actual_start":       actual_start.isoformat() if hasattr(actual_start, 'isoformat') else str(actual_start),
        "actual_end":         actual_end.isoformat()   if hasattr(actual_end,   'isoformat') else str(actual_end),
    }

   #Build a conflict dict for a resource that physically cannot reach the
    #trip's start location by the scheduled departure time.
def make_unreachable_conflict(trip_id, identifier, conflict_type, reason, earliest_arrival, actual_start, actual_end):
    return {
        "trip_id":            trip_id,
        "identifier":         identifier,
        "conflict_type":      conflict_type,
        "conflict_subtype":   "cannot_reach",
        "reason":             reason,
        "not_available_from": None,
        "not_available_to":   None,
        "earliest_available": earliest_arrival.isoformat() if hasattr(earliest_arrival, 'isoformat') else str(earliest_arrival),
        "actual_start":       actual_start.isoformat() if hasattr(actual_start, 'isoformat') else str(actual_start),
        "actual_end":         actual_end.isoformat()   if hasattr(actual_end,   'isoformat') else str(actual_end),
    }

 # Build a conflict dict for a trip that cannot proceed because an earlier
   # trip using the same resource already failed.
def make_cascade_conflict(trip_id, identifier, conflict_type, blocking_trip_id, actual_start, actual_end):
    return {
        "trip_id":            trip_id,
        "identifier":         identifier,
        "conflict_type":      conflict_type,
        "conflict_subtype":   "cascade",
        "reason":             f"Cannot proceed — depends on Trip {blocking_trip_id} which has a conflict",
        "not_available_from": None,
        "not_available_to":   None,
        "earliest_available": None,
        "blocking_trip_id":   blocking_trip_id,
        "actual_start":       actual_start.isoformat() if hasattr(actual_start, 'isoformat') else str(actual_start),
        "actual_end":         actual_end.isoformat()   if hasattr(actual_end,   'isoformat') else str(actual_end),
    }


# ─────────────────────────────────────────────
# FUEL CHECK
# ─────────────────────────────────────────────

"""Logic summary
    -------------
    1. If current fuel is already sufficient → no conflict.
    2. If the vehicle is currently AT a fuel station:
       a. Check whether a full tank would even cover the distance (capacity check).
       b. Check that the refuel + travel time doesn't push the departure into
          an unavailability window.
    3. Otherwise, search all fuel stations for the best (fastest) detour:
       a. The station must be reachable on current fuel.
       b. After filling up, the vehicle must be able to reach the trip start.
       c. The entire detour must fit inside an availability window."""
def check_vehicle_fuel(
    current_loc, start_loc, end_loc,
    current_fuel, fuel_capacity, consumption_rate,
    vehicle_speed, base_t0, actual_start, actual_end,
    identifier, avail_windows
):
    fill_time_secs = FUEL_FILL_TIME_MINS * 60

    #find distance and fuel needed to reach start location from current location
    dist_to_start = fetch_distance(current_loc, start_loc) or 0.0
    #fuel needed to reach start location from current location
    fuel_to_start = fuel_needed(dist_to_start, consumption_rate)


    if current_fuel >= fuel_to_start:
        return None

    if fetch_location_has_fuel(current_loc):
        if fuel_capacity < fuel_to_start:
            return make_fuel_conflict(
                None, identifier, "Vehicle",
                "Tank capacity insufficient — even when full cannot reach start location",
                actual_start, actual_end
            )
        travel_to_start_secs = travel_time_secs(dist_to_start, vehicle_speed)
        total_time_needed    = fill_time_secs + travel_to_start_secs
        detour_start         = actual_start - timedelta(seconds=total_time_needed)
        conflict, _ = overlaps_availability(detour_start, actual_start, avail_windows)
        if conflict:
            return make_fuel_stop_late_conflict(
                None, identifier, "Vehicle",
                "Insufficient fuel — refuel at current location but unable to reach start location on time ",
                actual_start, actual_end
            )
        return None

    fuel_stations     = fetch_fuel_stations()
    best_station      = None
    best_total_travel = float("inf")

    for station in fuel_stations:
        sid = station["location_id"]
        if sid == current_loc:
            continue
        dist_to_station    = fetch_distance(current_loc, sid)
        dist_station_start = fetch_distance(sid, start_loc)
        if dist_to_station is None or dist_station_start is None:
            continue
        if current_fuel < fuel_needed(dist_to_station, consumption_rate):
            continue
        if fuel_capacity < fuel_needed(dist_station_start, consumption_rate):
            continue
        total_travel = (
            travel_time_secs(dist_to_station,    vehicle_speed) +
            fill_time_secs +
            travel_time_secs(dist_station_start, vehicle_speed)
        )
        if total_travel < best_total_travel:
            best_total_travel = total_travel
            best_station      = station

    if best_station is None:
        return make_fuel_conflict(
            None, identifier, "Vehicle",
            "Insufficient fuel — cannot reach any fuel station on current fuel level",
            actual_start, actual_end
        )

    detour_start = actual_start - timedelta(seconds=best_total_travel)
    conflict, _ = overlaps_availability(detour_start, actual_start, avail_windows)
    if conflict:
        return make_fuel_stop_late_conflict(
            None, identifier, "Vehicle",
            f"Insufficient fuel — nearest viable fuel stop is {best_station['location_name']} but unable to reach on time ",
            actual_start, actual_end
        )

    return None


# ─────────────────────────────────────────────
# RESOURCE CHECK
# ─────────────────────────────────────────────
#checks perfored
#Availability check: does the resource have any unavailability windows that overlap the trip's actual start and end times?
#Fuel check (for vehicles): if the resource is a vehicle, does it have enough fuel to reach the trip's start location? If not, can it refuel in time?
#Reaching start location check: can the resource physically reach the trip's start location from its current location in time for the trip's actual start time?
def check_resource(identifier, conflict_type, current_loc, trip_start_loc,
                   speed, actual_start, actual_end, avail_windows, base_t0,
                   end_loc=None, current_fuel=None,
                   fuel_capacity=None, consumption_rate=None):

    conflict, window = overlaps_availability(actual_start, actual_end, avail_windows)
    if conflict:
        return make_unavailable_conflict(
            None, identifier, conflict_type, window, actual_start, actual_end
        )

    if conflict_type == "Vehicle" and current_fuel is not None:
        fuel_conflict = check_vehicle_fuel(
            current_loc, trip_start_loc, end_loc,
            current_fuel, fuel_capacity, consumption_rate,
            speed, base_t0, actual_start, actual_end,
            identifier, avail_windows
        )
        if fuel_conflict:
            return fuel_conflict

    if current_loc == trip_start_loc:
        return None

    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None:
        return make_unreachable_conflict(
            None, identifier, conflict_type,
            "No route found between locations",
            actual_start, actual_start, actual_end
        )
    if dist == 0:
        return None

    travel_secs = travel_time_secs(dist, speed)
    depart_time = actual_start - timedelta(seconds=travel_secs)

    travel_conflict, travel_window = overlaps_availability(
        depart_time, actual_start, avail_windows
    )
    if travel_conflict:
        free_at          = travel_window[1]
        earliest_arrival = free_at + timedelta(seconds=travel_secs)
        return make_unreachable_conflict(
            None, identifier, conflict_type,
            f"Unavailable during travel to start location: {travel_window[2]}",
            earliest_arrival, actual_start, actual_end
        )

    return None


# ─────────────────────────────────────────────
# RESOURCE STATE TRACKER
# ─────────────────────────────────────────────

def build_resource_states(trips, base_t0):
    """
    Pre-compute the *effective* location and fuel level for each resource
    at the start of every trip it is assigned to, assuming all prior trips
    in the sequence complete successfully (optimistic carry-forward).
    """
    vehicle_trips    = {}
    individual_trips = {}

    for trip in sorted(trips, key=lambda t: t["start_offset_secs"]):
        vn = trip["vehicle_number"]
        vehicle_trips.setdefault(vn, []).append(trip)
        for crew in trip["crew"]:
            individual_trips.setdefault(crew["individual_id"], []).append(trip)

    # ── vehicle states ──
    vehicle_states = {}

    for vn, vtrips in vehicle_trips.items():
        first            = vtrips[0]
        effective_loc    = first["vehicle_current_loc"]
        effective_fuel   = first["current_fuel"]
        consumption_rate = first["fuel_consumption_rate"]
        blocked_by       = None   # trip_id of first unresolved conflict in chain

        vehicle_states[vn] = {}

        for trip in vtrips:
            tid = trip["trip_id"]

            dist_deadhead = fetch_distance(effective_loc, trip["start_location_id"]) or 0.0
            dist_trip_leg = fetch_distance(trip["start_location_id"], trip["end_location_id"]) or 0.0
            fuel_this_leg = fuel_needed(dist_deadhead + dist_trip_leg, consumption_rate)

            vehicle_states[vn][tid] = {
                "effective_loc":  effective_loc,
                "effective_fuel": max(effective_fuel, 0.0),
                # If a prior trip in this vehicle's chain already failed,
                # record it so we can emit a cascade conflict instead of
                # re-checking location/fuel (which would be wrong anyway
                # since we're assuming the prior trip completed).
                "blocked_by":     blocked_by,
            }

            # Advance state — assume trip completes (optimistic carry-forward).
            # Cascade flag is what surfaces the problem on dependent trips.
            effective_fuel = max(effective_fuel - fuel_this_leg, 0.0)
            effective_loc  = trip["end_location_id"]

        # blocked_by is set by run_scheduler after it detects the first
        # real conflict, then injected back into subsequent trip states.
        # We do a second pass below once run_scheduler fills conflict_trips.

    # ── individual states ──
    individual_states = {}

    for iid, itrips in individual_trips.items():
        first         = itrips[0]
        effective_loc = None
        for crew in first["crew"]:
            if crew["individual_id"] == iid:
                effective_loc = crew["current_location_id"]
                break
        if effective_loc is None:
            effective_loc = first["start_location_id"]

        individual_states[iid] = {}

        for trip in itrips:
            tid = trip["trip_id"]
            individual_states[iid][tid] = {
                "effective_loc": effective_loc,
                "blocked_by":    None,   # filled by run_scheduler
            }
            effective_loc = trip["end_location_id"]

    return vehicle_states, individual_states


def apply_cascade_blocks(vehicle_states, individual_states,
                         failed_vehicle_trips, failed_individual_trips):
    """
    After the first pass of conflict detection, mark all downstream trips
    for each resource that had a failure.

    failed_vehicle_trips:     { vn  → set of trip_ids that directly failed }
    failed_individual_trips:  { iid → set of trip_ids that directly failed }

    For each resource, find the earliest failed trip in its ordered sequence,
    then set blocked_by on every subsequent trip in that sequence.
    """
    for vn, state_by_trip in vehicle_states.items():
        # trips in sequence order (dict insertion order is offset order
        # because build_resource_states walked them sorted)
        ordered_tids  = list(state_by_trip.keys())
        failed_for_vn = failed_vehicle_trips.get(vn, set())
        blocking_tid  = None

        for tid in ordered_tids:
            if blocking_tid is not None:
                # This trip comes after a failed one — mark cascade
                state_by_trip[tid]["blocked_by"] = blocking_tid
            if tid in failed_for_vn and blocking_tid is None:
                # First failure — all subsequent are blocked by this
                blocking_tid = tid

    for iid, state_by_trip in individual_states.items():
        ordered_tids   = list(state_by_trip.keys())
        failed_for_iid = failed_individual_trips.get(iid, set())
        blocking_tid   = None

        for tid in ordered_tids:
            if blocking_tid is not None:
                state_by_trip[tid]["blocked_by"] = blocking_tid
            if tid in failed_for_iid and blocking_tid is None:
                blocking_tid = tid


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def run_scheduler(plan_id, date_str, time_str):

    # Guard: refuse to evaluate plans for dates already in the past,
    plan_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    if plan_date < datetime.today().date():
        return {
            "feasible":  False,
            "schedule":  [],
            "conflicts": [],
            "error":     f"Cannot check plan for a past date ({date_str}). Please provide today's date or a future date."
        }

    base_t0, trips = fetch_plan_data(plan_id, date_str, time_str)
    vehicle_avail, individual_avail = fetch_availability(plan_id)
    vehicle_states, individual_states = build_resource_states(trips, base_t0)

    # ── Pass 1: check every trip independently, collect direct failures ──
    direct_conflicts         = []   # conflicts from real checks
    failed_vehicle_trips     = {}   # vn  → set of trip_ids that directly failed
    failed_individual_trips  = {}   # iid → set of trip_ids that directly failed
    schedule_output          = []
    # Sort trips by their start offset to process in chronological order.
    sorted_trips = sorted(trips, key=lambda t: t["start_offset_secs"])

    for trip in sorted_trips:
        tid          = trip["trip_id"]
        actual_start = base_t0 + timedelta(seconds=trip["start_offset_secs"])
        actual_end   = actual_start + timedelta(seconds=trip["duration_secs"])

        schedule_output.append({
            "trip_id":      tid,
            "actual_start": actual_start.isoformat(),
            "actual_end":   actual_end.isoformat(),
        })

        # ── Vehicle ──
        vn     = trip["vehicle_number"]
        vstate = vehicle_states[vn][tid]

        c = check_resource(
            vn, "Vehicle",
            vstate["effective_loc"],
            trip["start_location_id"],
            trip["vehicle_speed"],
            actual_start, actual_end,
            vehicle_avail.get(vn, []),
            base_t0,
            end_loc=trip["end_location_id"],
            current_fuel=vstate["effective_fuel"],
            fuel_capacity=trip["fuel_capacity"],
            consumption_rate=trip["fuel_consumption_rate"]
        )
        if c:
            c["trip_id"] = tid
            direct_conflicts.append(c)
            failed_vehicle_trips.setdefault(vn, set()).add(tid)

        # ── Crew ──
        for crew in trip["crew"]:
            iid    = crew["individual_id"]
            istate = individual_states.get(iid, {}).get(tid)
            eff_crew_loc = istate["effective_loc"] if istate else crew["current_location_id"]

            c = check_resource(
                crew["name"], "Individual",
                eff_crew_loc,
                trip["start_location_id"],
                INDIVIDUAL_SPEED_KMH,
                actual_start, actual_end,
                individual_avail.get(iid, []),
                base_t0
            )
            if c:
                c["trip_id"] = tid
                direct_conflicts.append(c)
                failed_individual_trips.setdefault(iid, set()).add(tid)

    # ── Pass 2: mark cascade blocks on downstream trips ──
    apply_cascade_blocks(
        vehicle_states, individual_states,
        failed_vehicle_trips, failed_individual_trips
    )

    # ── Pass 3: emit cascade conflicts for blocked downstream trips ──
    # Only emit cascade if the trip has no direct conflict already
    # (avoids double-reporting).
    direct_conflict_trip_ids = {c["trip_id"] for c in direct_conflicts}
    cascade_conflicts = []

    for trip in sorted_trips:
        tid          = trip["trip_id"]
        actual_start = base_t0 + timedelta(seconds=trip["start_offset_secs"])
        actual_end   = actual_start + timedelta(seconds=trip["duration_secs"])

        # Vehicle cascade
        vn     = trip["vehicle_number"]
        vstate = vehicle_states[vn][tid]
        if vstate["blocked_by"] is not None and tid not in direct_conflict_trip_ids:
            cascade_conflicts.append(make_cascade_conflict(
                tid, vn, "Vehicle",
                vstate["blocked_by"],
                actual_start, actual_end
            ))
            direct_conflict_trip_ids.add(tid)   # don't double-add from crew check

        # Individual cascade
        for crew in trip["crew"]:
            iid    = crew["individual_id"]
            istate = individual_states.get(iid, {}).get(tid)
            if istate and istate["blocked_by"] is not None and tid not in direct_conflict_trip_ids:
                cascade_conflicts.append(make_cascade_conflict(
                    tid, crew["name"], "Individual",
                    istate["blocked_by"],
                    actual_start, actual_end
                ))

    all_conflicts    = direct_conflicts + cascade_conflicts
    overall_feasible = len(all_conflicts) == 0

    schedule_output.sort(key=lambda x: x["actual_start"])

    return {
        "feasible":  overall_feasible,
        "schedule":  schedule_output,
        "conflicts": all_conflicts
    }