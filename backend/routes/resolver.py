from datetime import datetime, timedelta
from db import get_connection
from routes.scheduler import (
    fetch_distance, travel_time_secs, overlaps_availability,
    INDIVIDUAL_SPEED_KMH
)


def fetch_plan_assigned_resources(plan_id):
    """Get all vehicle numbers and individual ids already assigned in this plan."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT vehicle_number FROM trips WHERE plan_id = %s
    """, (plan_id,))
    assigned_vehicles = {r[0] for r in cur.fetchall()}

    cur.execute("""
        SELECT DISTINCT tc.individual_id
        FROM trip_crew tc
        JOIN trips t ON t.trip_id = tc.trip_id
        WHERE t.plan_id = %s
    """, (plan_id,))
    assigned_individuals = {r[0] for r in cur.fetchall()}

    cur.close()
    conn.close()
    return assigned_vehicles, assigned_individuals


def fetch_same_type_vehicles(vehicle_number, exclude_numbers):
    """Get all vehicles of the same type, excluding already assigned ones."""
    conn = get_connection()
    cur = conn.cursor()

    exclude_list = list(exclude_numbers) if exclude_numbers else ['__none__']

    cur.execute("""
        SELECT v.vehicle_number, v.vehicle_name, v.current_location_id, vt.default_speed
        FROM vehicles v
        JOIN vehicle_types vt ON vt.vehicle_type_id = v.vehicle_type_id
        WHERE vt.vehicle_type_id = (
            SELECT vt2.vehicle_type_id
            FROM vehicles v2
            JOIN vehicle_types vt2 ON vt2.vehicle_type_id = v2.vehicle_type_id
            WHERE v2.vehicle_number = %s
        )
        AND v.vehicle_number != %s
        AND v.vehicle_number != ALL(%s)
    """, (vehicle_number, vehicle_number, exclude_list))
    rows = cur.fetchall()

    if not rows:
        cur.close()
        conn.close()
        return []

    cur.execute("""
        SELECT vehicle_number, not_available_from, not_available_to, reason
        FROM vehicle_availability
        WHERE vehicle_number = ANY(%s)
    """, ([r[0] for r in rows],))
    avail_rows = cur.fetchall()

    cur.close()
    conn.close()

    avail_map = {}
    for r in avail_rows:
        avail_map.setdefault(r[0], []).append((
            r[1].replace(tzinfo=None) if hasattr(r[1], 'tzinfo') else r[1],
            r[2].replace(tzinfo=None) if hasattr(r[2], 'tzinfo') else r[2],
            r[3]
        ))

    return [
        {
            "vehicle_number":   r[0],
            "vehicle_name":     r[1],
            "current_location": r[2],
            "speed":            float(r[3]),
            "avail_windows":    avail_map.get(r[0], [])
        }
        for r in rows
    ]


def fetch_same_type_individuals(individual_id, exclude_ids):
    """Get all individuals of the same crew type, excluding already assigned ones."""
    conn = get_connection()
    cur = conn.cursor()

    exclude_list = list(exclude_ids) if exclude_ids else [-1]

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
        cur.close()
        conn.close()
        return []

    cur.execute("""
        SELECT individual_id, not_available_from, not_available_to, reason
        FROM individual_availability
        WHERE individual_id = ANY(%s)
    """, ([r[0] for r in rows],))
    avail_rows = cur.fetchall()

    cur.close()
    conn.close()

    avail_map = {}
    for r in avail_rows:
        avail_map.setdefault(r[0], []).append((
            r[1].replace(tzinfo=None) if hasattr(r[1], 'tzinfo') else r[1],
            r[2].replace(tzinfo=None) if hasattr(r[2], 'tzinfo') else r[2],
            r[3]
        ))

    return [
        {
            "individual_id":    r[0],
            "name":             r[1],
            "current_location": r[2],
            "crew_type":        r[3],
            "avail_windows":    avail_map.get(r[0], [])
        }
        for r in rows
    ]


def is_resource_available_and_reachable(current_loc, trip_start_loc, speed,
                                         actual_start, actual_end, avail_windows, base_t0):
    """
    Check if a replacement resource is both available and can physically reach
    the trip start location in time.

    Rules:
    1. Must be free from base_t0 → actual_end
       (covers travel prep + loading + trip duration)
    2. Must be free during travel window: (base_t0 - travel_secs) → base_t0
       (they must travel and arrive at start location before plan begins)
    """
    # 1. Available from base_t0 to actual_end
    conflict, _ = overlaps_availability(base_t0, actual_end, avail_windows)
    if conflict:
        return False, None

    # 2. Reachability
    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None:
        return False, None

    if dist == 0:
        return True, actual_start

    # Must arrive at start location by base_t0
    # So must depart at base_t0 - travel_secs
    travel_secs = travel_time_secs(dist, speed)
    depart_time = base_t0 - timedelta(seconds=travel_secs)

    # Must be free during travel window (depart_time → base_t0)
    travel_conflict, _ = overlaps_availability(depart_time, base_t0, avail_windows)
    if travel_conflict:
        return False, None

    return True, actual_start


def resolve_conflicts(conflicts, plan_id, trip_map, base_t0):
    """
    For each conflict, attempt to find a replacement resource.
    - Excludes resources already assigned to the plan
    - Checks availability from base_t0 to actual_end
    - Checks reachability: must depart at base_t0 - travel_secs and be free then
    - Picks closest available replacement (least travel distance)
    Returns list of resolution dicts.
    """
    assigned_vehicles, assigned_individuals = fetch_plan_assigned_resources(plan_id)

    used_replacements_vehicles    = set()
    used_replacements_individuals = set()

    resolutions = []

    for conflict in conflicts:
        trip_id    = conflict["trip_id"]
        identifier = conflict["identifier"]
        ctype      = conflict["conflict_type"]

        # Parse datetimes
        actual_start = conflict["actual_start"]
        actual_end   = conflict["actual_end"]
        if isinstance(actual_start, str):
            actual_start = datetime.fromisoformat(actual_start)
        if isinstance(actual_end, str):
            actual_end = datetime.fromisoformat(actual_end)

        trip = trip_map.get(trip_id)
        if not trip:
            resolutions.append({
                "trip_id":       trip_id,
                "original":      identifier,
                "conflict_type": ctype,
                "replacement":   None,
                "resolved":      False
            })
            continue

        trip_start_loc = trip["start_location_id"]

        # ── Vehicle conflict ──
        if ctype == "Vehicle":
            candidates = fetch_same_type_vehicles(
                identifier,
                assigned_vehicles | used_replacements_vehicles
            )

            best      = None
            best_dist = float("inf")

            for candidate in candidates:
                ok, _ = is_resource_available_and_reachable(
                    candidate["current_location"],
                    trip_start_loc,
                    candidate["speed"],
                    actual_start,
                    actual_end,
                    candidate["avail_windows"],
                    base_t0
                )
                if ok:
                    dist = fetch_distance(candidate["current_location"], trip_start_loc) or 0.0
                    if dist < best_dist:
                        best_dist = dist
                        best = candidate

            if best:
                used_replacements_vehicles.add(best["vehicle_number"])
                resolutions.append({
                    "trip_id":          trip_id,
                    "original":         identifier,
                    "conflict_type":    "Vehicle",
                    "replacement":      best["vehicle_number"],
                    "replacement_name": best["vehicle_name"],
                    "resolved":         True
                })
            else:
                resolutions.append({
                    "trip_id":       trip_id,
                    "original":      identifier,
                    "conflict_type": "Vehicle",
                    "replacement":   None,
                    "resolved":      False
                })

        # ── Individual conflict ──
        elif ctype == "Individual":
            individual_id = next(
                (c["individual_id"] for c in trip["crew"] if c["name"] == identifier),
                None
            )

            if individual_id is None:
                resolutions.append({
                    "trip_id":       trip_id,
                    "original":      identifier,
                    "conflict_type": "Individual",
                    "replacement":   None,
                    "resolved":      False
                })
                continue

            candidates = fetch_same_type_individuals(
                individual_id,
                assigned_individuals | used_replacements_individuals
            )

            best      = None
            best_dist = float("inf")

            for candidate in candidates:
                ok, _ = is_resource_available_and_reachable(
                    candidate["current_location"],
                    trip_start_loc,
                    INDIVIDUAL_SPEED_KMH,
                    actual_start,
                    actual_end,
                    candidate["avail_windows"],
                    base_t0
                )
                if ok:
                    dist = fetch_distance(candidate["current_location"], trip_start_loc) or 0.0
                    if dist < best_dist:
                        best_dist = dist
                        best = candidate

            if best:
                used_replacements_individuals.add(best["individual_id"])
                resolutions.append({
                    "trip_id":          trip_id,
                    "original":         identifier,
                    "conflict_type":    "Individual",
                    "replacement":      best["name"],
                    "replacement_name": best["name"],
                    "crew_type":        best["crew_type"],
                    "resolved":         True
                })
            else:
                resolutions.append({
                    "trip_id":       trip_id,
                    "original":      identifier,
                    "conflict_type": "Individual",
                    "replacement":   None,
                    "resolved":      False
                })

    return resolutions
