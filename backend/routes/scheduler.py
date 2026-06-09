from datetime import datetime, timedelta
from db import get_connection

INDIVIDUAL_SPEED_KMH = 40.0


# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fetch_plan_data(plan_id, date_str, time_str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT default_start_time FROM plans WHERE plan_id = %s", (plan_id,))
    row = cur.fetchone()
    default_start = row[0]  # comes back as datetime.time from Postgres

    # Resolve T0
    if time_str:
        t0_time = datetime.strptime(time_str, "%H:%M").time()
    else:
        t0_time = default_start  # already a time object

    base_date = datetime.strptime(date_str, "%Y-%m-%d")
    base_t0 = datetime.combine(base_date, t0_time)

    cur.execute("""
        SELECT
            t.trip_id,
            t.vehicle_number,
            t.start_offset,
            t.duration,
            r.start_location_id,
            r.end_location_id,
            vt.default_speed,
            v.current_location_id
        FROM trips t
        JOIN routes r       ON r.route_id          = t.route_id
        JOIN vehicles v     ON v.vehicle_number     = t.vehicle_number
        JOIN vehicle_types vt ON vt.vehicle_type_id = v.vehicle_type_id
        WHERE t.plan_id = %s
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
            "trip_id":             row[0],
            "vehicle_number":      row[1],
            "start_offset_secs":   time_to_secs(row[2]),
            "duration_secs":       time_to_secs(row[3]),
            "start_location_id":   row[4],
            "end_location_id":     row[5],
            "vehicle_speed":       float(row[6]),
            "vehicle_current_loc": row[7],
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
    cur = conn.cursor()
    cur.execute("""
        SELECT distance FROM routes
        WHERE start_location_id = %s AND end_location_id = %s
        LIMIT 1
    """, (from_loc, to_loc))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return float(row[0]) if row else None


def fetch_availability(plan_id):
    conn = get_connection()
    cur = conn.cursor()

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


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def travel_time_secs(distance_km, speed_kmh):
    if distance_km is None or distance_km == 0:
        return 0.0
    return (distance_km / speed_kmh) * 3600.0


def overlaps_availability(start_dt, end_dt, avail_windows):
    """Returns (conflict: bool, matching window or None)"""
    for not_from, not_to, reason in avail_windows:
        # Strip timezone if present for comparison
        nf = not_from.replace(tzinfo=None) if hasattr(not_from, 'tzinfo') else not_from
        nt = not_to.replace(tzinfo=None) if hasattr(not_to, 'tzinfo') else not_to
        if start_dt < nt and end_dt > nf:
            return True, (nf, nt, reason)
    return False, None


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
        "actual_end":         actual_end.isoformat() if hasattr(actual_end, 'isoformat') else str(actual_end),
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
        "actual_end":         actual_end.isoformat() if hasattr(actual_end, 'isoformat') else str(actual_end),
    }


def check_resource(identifier, conflict_type, current_loc, trip_start_loc,
                   speed, actual_start, actual_end, avail_windows, base_t0):

    # 1. Availability during the trip itself
    conflict, window = overlaps_availability(actual_start, actual_end, avail_windows)
    if conflict:
        return make_unavailable_conflict(
            None, identifier, conflict_type, window, actual_start, actual_end
        )

    # 2. Reachability — only if available during trip
    if current_loc == trip_start_loc:
        return None  # already there, no issue

    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None:
        return make_unreachable_conflict(
            None, identifier, conflict_type,
            "No route found between locations",
            actual_start, actual_start, actual_end
        )

    if dist == 0:
        return None  # same location

    # Work backwards — when must they depart to arrive by actual_start?
    travel_secs = travel_time_secs(dist, speed)
    depart_time = actual_start - timedelta(seconds=travel_secs)
    earliest_arrival = actual_start  # they arrive exactly on time if they depart at depart_time

    # Check if they are free during the travel window (depart_time → actual_start)
    travel_conflict, travel_window = overlaps_availability(
        depart_time, actual_start, avail_windows
    )
    if travel_conflict:
        # They are busy during the time they need to be travelling
        # Earliest they could arrive = travel_window end + travel_time
        free_at = travel_window[1]  # when they become free
        earliest_arrival = free_at + timedelta(seconds=travel_secs)
        return make_unreachable_conflict(
            None, identifier, conflict_type,
            f"Unavailable during travel window: {travel_window[2]}",
            earliest_arrival, actual_start, actual_end
        )

    return None  # free during travel window, can reach in time


# ─────────────────────────────────────────────
# SHARED RESOURCE DETECTION
# ─────────────────────────────────────────────

def find_shared_resource_groups(trips):
    vehicle_to_trips = {}
    individual_to_trips = {}

    for trip in trips:
        tid = trip["trip_id"]
        vehicle_to_trips.setdefault(trip["vehicle_number"], set()).add(tid)
        for crew in trip["crew"]:
            individual_to_trips.setdefault(crew["individual_id"], set()).add(tid)

    parent = {t["trip_id"]: t["trip_id"] for t in trips}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for tids in vehicle_to_trips.values():
        tids = list(tids)
        for i in range(1, len(tids)):
            union(tids[0], tids[i])

    for tids in individual_to_trips.values():
        tids = list(tids)
        for i in range(1, len(tids)):
            union(tids[0], tids[i])

    groups = {}
    for trip in trips:
        tid = trip["trip_id"]
        groups.setdefault(find(tid), set()).add(tid)

    shared_groups    = [g for g in groups.values() if len(g) > 1]
    independent_trips = [g for g in groups.values() if len(g) == 1]
    return shared_groups, independent_trips


# ─────────────────────────────────────────────
# TRIP WINDOW COMPUTATION
# ─────────────────────────────────────────────

def compute_trip_window(trip, t0, prev_end_times):
    """
    actual_start = max(t0 + offset, arrival of all shared resources)
    """
    base_start = t0 + timedelta(seconds=trip["start_offset_secs"])
    latest_arrival = base_start

    vn = trip["vehicle_number"]
    if vn in prev_end_times:
        prev_end_dt, prev_end_loc = prev_end_times[vn]
        dist = fetch_distance(prev_end_loc, trip["start_location_id"])
        if dist is not None:
            arrival = prev_end_dt + timedelta(seconds=travel_time_secs(dist, trip["vehicle_speed"]))
            latest_arrival = max(latest_arrival, arrival)

    for crew in trip["crew"]:
        iid = crew["individual_id"]
        if iid in prev_end_times:
            prev_end_dt, prev_end_loc = prev_end_times[iid]
            dist = fetch_distance(prev_end_loc, trip["start_location_id"])
            if dist is not None:
                arrival = prev_end_dt + timedelta(seconds=travel_time_secs(dist, INDIVIDUAL_SPEED_KMH))
                latest_arrival = max(latest_arrival, arrival)

    actual_start = latest_arrival
    actual_end   = actual_start + timedelta(seconds=trip["duration_secs"])
    return actual_start, actual_end


# ─────────────────────────────────────────────
# BRANCH AND BOUND
# ─────────────────────────────────────────────

def branch_and_bound_schedule(group_trip_ids, trip_map, t0, vehicle_avail, individual_avail):
    trips = [trip_map[tid] for tid in group_trip_ids]

    best_valid_schedule   = None
    best_valid_end        = None
    best_fallback_schedule = None
    best_fallback_end     = None
    best_fallback_conflicts = None
    upper_bound           = None

    def backtrack(remaining, scheduled, prev_end_times, current_conflicts):
        nonlocal best_valid_schedule, best_valid_end
        nonlocal best_fallback_schedule, best_fallback_end, best_fallback_conflicts
        nonlocal upper_bound

        if not remaining:
            last_end = max(end for _, _, end in scheduled)
            if not current_conflicts:
                if best_valid_end is None or last_end < best_valid_end:
                    best_valid_end     = last_end
                    best_valid_schedule = list(scheduled)
                    upper_bound        = last_end
            else:
                if best_fallback_end is None or last_end < best_fallback_end:
                    best_fallback_end      = last_end
                    best_fallback_schedule = list(scheduled)
                    best_fallback_conflicts = list(current_conflicts)
            return

        for i, trip in enumerate(remaining):
            actual_start, actual_end = compute_trip_window(trip, t0, prev_end_times)

            if upper_bound is not None and actual_end > upper_bound:
                continue

            trip_conflicts = []
            vn = trip["vehicle_number"]

            # ── Shared vehicle: availability first, reachability only if available ──
            if vn in prev_end_times:
                conflict, window = overlaps_availability(actual_start, actual_end, vehicle_avail.get(vn, []))
                if conflict:
                    c = make_unavailable_conflict(trip["trip_id"], vn, "Vehicle", window, actual_start, actual_end)
                    trip_conflicts.append(c)
                # No reachability check for shared vehicle here —
                # its arrival time already computed in compute_trip_window

            # ── Shared crew: availability check ──
            for crew in trip["crew"]:
                iid = crew["individual_id"]
                if iid in prev_end_times:
                    conflict, window = overlaps_availability(actual_start, actual_end, individual_avail.get(iid, []))
                    if conflict:
                        c = make_unavailable_conflict(trip["trip_id"], crew["name"], "Individual", window, actual_start, actual_end)
                        trip_conflicts.append(c)

            # ── Non-shared resources ──
            # Vehicle
            if vn not in prev_end_times:
                c = check_resource(
                    vn, "Vehicle",
                    trip["vehicle_current_loc"], trip["start_location_id"],
                    trip["vehicle_speed"], actual_start, actual_end,
                    vehicle_avail.get(vn, []), t0
                )
                if c:
                    c["trip_id"] = trip["trip_id"]
                    trip_conflicts.append(c)

            # Crew
            for crew in trip["crew"]:
                iid = crew["individual_id"]
                if iid not in prev_end_times:
                    c = check_resource(
                        crew["name"], "Individual",
                        crew["current_location_id"], trip["start_location_id"],
                        INDIVIDUAL_SPEED_KMH, actual_start, actual_end,
                        individual_avail.get(iid, []), t0
                    )
                    if c:
                        c["trip_id"] = trip["trip_id"]
                        trip_conflicts.append(c)

            # Update state for next trip
            new_prev = dict(prev_end_times)
            new_prev[vn] = (actual_end, trip["end_location_id"])
            for crew in trip["crew"]:
                new_prev[crew["individual_id"]] = (actual_end, trip["end_location_id"])

            backtrack(
                remaining[:i] + remaining[i+1:],
                scheduled + [(trip, actual_start, actual_end)],
                new_prev,
                current_conflicts + trip_conflicts
            )

    backtrack(trips, [], {}, [])

    if best_valid_schedule is not None:
        return best_valid_schedule, [], True
    else:
        return best_fallback_schedule, best_fallback_conflicts or [], False


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def run_scheduler(plan_id, date_str, time_str):
    base_t0, trips = fetch_plan_data(plan_id, date_str, time_str)
    trip_map = {t["trip_id"]: t for t in trips}
    vehicle_avail, individual_avail = fetch_availability(plan_id)

    shared_groups, independent_groups = find_shared_resource_groups(trips)

    all_conflicts  = []
    schedule_output = []
    overall_feasible = True
    scheduled_trip_ids = set()

    # ── Independent trips ──
    for group in independent_groups:
        tid = list(group)[0]
        if tid in scheduled_trip_ids:
            continue
        scheduled_trip_ids.add(tid)

        trip = trip_map[tid]
        actual_start = base_t0 + timedelta(seconds=trip["start_offset_secs"])
        actual_end   = actual_start + timedelta(seconds=trip["duration_secs"])

        schedule_output.append({
            "trip_id":      tid,
            "actual_start": actual_start.isoformat(),
            "actual_end":   actual_end.isoformat(),
            "sequenced":    False
        })

        # Vehicle
        vn = trip["vehicle_number"]
        c = check_resource(
            vn, "Vehicle",
            trip["vehicle_current_loc"], trip["start_location_id"],
            trip["vehicle_speed"], actual_start, actual_end,
            vehicle_avail.get(vn, []), base_t0
        )
        if c:
            c["trip_id"] = tid
            overall_feasible = False
            all_conflicts.append(c)

        # Crew
        for crew in trip["crew"]:
            iid = crew["individual_id"]
            c = check_resource(
                crew["name"], "Individual",
                crew["current_location_id"], trip["start_location_id"],
                INDIVIDUAL_SPEED_KMH, actual_start, actual_end,
                individual_avail.get(iid, []), base_t0
            )
            if c:
                c["trip_id"] = tid
                overall_feasible = False
                all_conflicts.append(c)

    # ── Shared resource groups ──
    for group in shared_groups:
        best_schedule, group_conflicts, is_valid = branch_and_bound_schedule(
            group, trip_map, base_t0, vehicle_avail, individual_avail
        )

        if not is_valid:
            overall_feasible = False

        if best_schedule:
            for trip, actual_start, actual_end in best_schedule:
                tid = trip["trip_id"]
                if tid in scheduled_trip_ids:
                    continue
                scheduled_trip_ids.add(tid)
                schedule_output.append({
                    "trip_id":      tid,
                    "actual_start": actual_start.isoformat(),
                    "actual_end":   actual_end.isoformat(),
                    "sequenced":    True
                })

        all_conflicts.extend(group_conflicts)

    schedule_output.sort(key=lambda x: x["actual_start"])

    return {
        "feasible":  overall_feasible and len(all_conflicts) == 0,
        "schedule":  schedule_output,
        "conflicts": all_conflicts
    }