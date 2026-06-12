from datetime import datetime, timedelta
from db import get_connection

INDIVIDUAL_SPEED_KMH = 40.0
FUEL_FILL_TIME_MINS  = 10


# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fetch_plan_data(plan_id, date_str, time_str):
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT default_start_time FROM plans WHERE plan_id = %s", (plan_id,))
    row           = cur.fetchone()
    default_start = row[0]

    if time_str:
        t0_time = datetime.strptime(time_str, "%H:%M").time()
    else:
        t0_time = default_start

    base_date = datetime.strptime(date_str, "%Y-%m-%d")
    base_t0   = datetime.combine(base_date, t0_time)

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

        cur.execute("""
            SELECT i.individual_id, i.current_location_id, i.name
            FROM trip_crew tc
            JOIN individuals i ON i.individual_id = tc.individual_id
            WHERE tc.trip_id = %s
        """, (trip_id,))
        crew = cur.fetchall()

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


def fetch_distance(from_loc, to_loc):
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

def travel_time_secs(distance_km, speed_kmh):
    if distance_km is None or distance_km == 0:
        return 0.0
    return (distance_km / speed_kmh) * 3600.0


def fuel_needed(distance_km, consumption_rate):
    if distance_km is None or distance_km == 0:
        return 0.0
    return distance_km * consumption_rate


def overlaps_availability(start_dt, end_dt, avail_windows):
    """Returns (conflict: bool, matching window or None)."""
    for not_from, not_to, reason in avail_windows:
        nf = not_from.replace(tzinfo=None) if not_from.tzinfo is not None else not_from
        nt = not_to.replace(tzinfo=None)   if not_to.tzinfo   is not None else not_to
        if start_dt < nt and end_dt > nf:
            return True, (nf, nt, reason)
    return False, None


# ─────────────────────────────────────────────
# CONFLICT MAKERS
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# FUEL CHECK
# ─────────────────────────────────────────────

def check_vehicle_fuel(
    current_loc, start_loc, end_loc,
    current_fuel, fuel_capacity, consumption_rate,
    vehicle_speed, base_t0, actual_start, actual_end,
    identifier, avail_windows
):
    fill_time_secs = FUEL_FILL_TIME_MINS * 60

    dist_to_start = fetch_distance(current_loc, start_loc) or 0.0
    fuel_to_start = fuel_needed(dist_to_start, consumption_rate)

    # ── Case 1: enough fuel to reach start_loc ──
    if current_fuel >= fuel_to_start:
        return None

    # ── Case 2: fuel station at current location ──
    if fetch_location_has_fuel(current_loc):
        if fuel_capacity < fuel_to_start:
            return make_fuel_conflict(
                None, identifier, "Vehicle",
                "Tank capacity insufficient — even when full cannot reach start location",
                actual_start, actual_end
            )

        travel_to_start_secs = travel_time_secs(dist_to_start, vehicle_speed)
        total_time_needed    = fill_time_secs + travel_to_start_secs
        detour_start         = base_t0 - timedelta(seconds=total_time_needed)

        conflict, _ = overlaps_availability(detour_start, base_t0, avail_windows)
        if conflict:
            return make_fuel_stop_late_conflict(
                None, identifier, "Vehicle",
                "Insufficient fuel — refuel at current location but unavailable during travel window to start location",
                actual_start, actual_end
            )

        return None

    # ── Case 3: no fuel station at current location ──
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

    detour_start = base_t0 - timedelta(seconds=best_total_travel)

    conflict, _ = overlaps_availability(detour_start, base_t0, avail_windows)
    if conflict:
        return make_fuel_stop_late_conflict(
            None, identifier, "Vehicle",
            f"Insufficient fuel — nearest viable fuel stop is {best_station['location_name']} but unavailable during detour window",
            actual_start, actual_end
        )

    return None


# ─────────────────────────────────────────────
# RESOURCE CHECK
# ─────────────────────────────────────────────

def check_resource(identifier, conflict_type, current_loc, trip_start_loc,
                   speed, actual_start, actual_end, avail_windows, base_t0,
                   end_loc=None, current_fuel=None,
                   fuel_capacity=None, consumption_rate=None):
    """
    Check order:
    1. Availability: base_t0 → actual_end
    2. Fuel check (vehicles only)
    3. Reachability: must depart base_t0 - travel_secs, free during travel window
    """

    # ── 1. Availability ──
    conflict, window = overlaps_availability(base_t0, actual_end, avail_windows)
    if conflict:
        return make_unavailable_conflict(
            None, identifier, conflict_type, window, actual_start, actual_end
        )

    # ── 2. Fuel check (vehicles only) ──
    if conflict_type == "Vehicle" and current_fuel is not None:
        fuel_conflict = check_vehicle_fuel(
            current_loc, trip_start_loc, end_loc,
            current_fuel, fuel_capacity, consumption_rate,
            speed, base_t0, actual_start, actual_end,
            identifier, avail_windows
        )
        if fuel_conflict:
            return fuel_conflict

    # ── 3. Reachability ──
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
    depart_time = base_t0 - timedelta(seconds=travel_secs)

    travel_conflict, travel_window = overlaps_availability(
        depart_time, base_t0, avail_windows
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
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def run_scheduler(plan_id, date_str, time_str):
    base_t0, trips = fetch_plan_data(plan_id, date_str, time_str)
    vehicle_avail, individual_avail = fetch_availability(plan_id)

    all_conflicts    = []
    schedule_output  = []
    overall_feasible = True

    for trip in trips:
        tid          = trip["trip_id"]
        actual_start = base_t0 + timedelta(seconds=trip["start_offset_secs"])
        actual_end   = actual_start + timedelta(seconds=trip["duration_secs"])

        schedule_output.append({
            "trip_id":      tid,
            "actual_start": actual_start.isoformat(),
            "actual_end":   actual_end.isoformat(),
            "sequenced":    False
        })

        # ── Vehicle check ──
        vn = trip["vehicle_number"]
        c  = check_resource(
            vn, "Vehicle",
            trip["vehicle_current_loc"], trip["start_location_id"],
            trip["vehicle_speed"], actual_start, actual_end,
            vehicle_avail.get(vn, []), base_t0,
            end_loc=trip["end_location_id"],
            current_fuel=trip["current_fuel"],
            fuel_capacity=trip["fuel_capacity"],
            consumption_rate=trip["fuel_consumption_rate"]
        )
        if c:
            c["trip_id"] = tid
            overall_feasible = False
            all_conflicts.append(c)

        # ── Crew checks ──
        for crew in trip["crew"]:
            iid = crew["individual_id"]
            c   = check_resource(
                crew["name"], "Individual",
                crew["current_location_id"], trip["start_location_id"],
                INDIVIDUAL_SPEED_KMH, actual_start, actual_end,
                individual_avail.get(iid, []), base_t0
            )
            if c:
                c["trip_id"] = tid
                overall_feasible = False
                all_conflicts.append(c)

    schedule_output.sort(key=lambda x: x["actual_start"])

    return {
        "feasible":  overall_feasible and len(all_conflicts) == 0,
        "schedule":  schedule_output,
        "conflicts": all_conflicts
    }