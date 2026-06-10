from datetime import datetime, timedelta
from db import get_connection
from routes.scheduler import (
    fetch_distance, travel_time_secs, overlaps_availability,
    fetch_fuel_stations, fetch_location_has_fuel,
    fuel_needed, check_vehicle_fuel,
    INDIVIDUAL_SPEED_KMH, FUEL_FILL_TIME_MINS
)


# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fetch_plan_assigned_resources(plan_id):
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT DISTINCT vehicle_number FROM trips WHERE plan_id = %s", (plan_id,))
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
    conn = get_connection()
    cur  = conn.cursor()

    exclude_list = list(exclude_numbers) if exclude_numbers else ['__none__']

    cur.execute("""
        SELECT
            v.vehicle_number,
            v.vehicle_name,
            v.current_location_id,
            vt.default_speed,
            v.current_fuel_level,
            vt.fuel_capacity,
            vt.fuel_consumption_rate
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
            "vehicle_number":        r[0],
            "vehicle_name":          r[1],
            "current_location":      r[2],
            "speed":                 float(r[3]),
            "current_fuel":          float(r[4]),
            "fuel_capacity":         float(r[5]),
            "fuel_consumption_rate": float(r[6]),
            "avail_windows":         avail_map.get(r[0], [])
        }
        for r in rows
    ]


def fetch_same_type_individuals(individual_id, exclude_ids):
    conn = get_connection()
    cur  = conn.cursor()

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


def fetch_original_vehicle_capacity(vehicle_number):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT vt.max_load_capacity
        FROM vehicles v
        JOIN vehicle_types vt ON vt.vehicle_type_id = v.vehicle_type_id
        WHERE v.vehicle_number = %s
    """, (vehicle_number,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return float(row[0]) if row else 0.0


def fetch_any_capable_vehicles(
    exclude_numbers, min_capacity,
    trip_start_loc, trip_end_loc,
    base_t0, actual_start, actual_end
):
    conn = get_connection()
    cur  = conn.cursor()

    exclude_list = list(exclude_numbers) if exclude_numbers else ['__none__']

    cur.execute("""
        SELECT
            v.vehicle_number,
            v.vehicle_name,
            v.current_location_id,
            vt.default_speed,
            v.current_fuel_level,
            vt.fuel_capacity,
            vt.fuel_consumption_rate,
            vt.max_load_capacity
        FROM vehicles v
        JOIN vehicle_types vt ON vt.vehicle_type_id = v.vehicle_type_id
        WHERE v.vehicle_number != ALL(%s)
    """, (exclude_list,))
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
            r[1].replace(tzinfo=None) if hasattr(r[1], 'tzinfo') and r[1].tzinfo else r[1],
            r[2].replace(tzinfo=None) if hasattr(r[2], 'tzinfo') and r[2].tzinfo else r[2],
            r[3]
        ))

    candidates = []
    for r in rows:
        vn               = r[0]
        current_loc      = r[2]
        speed            = float(r[3])
        current_fuel     = float(r[4])
        fuel_capacity    = float(r[5])
        consumption_rate = float(r[6])
        max_load         = float(r[7])
        avail_windows    = avail_map.get(vn, [])

        candidate = {
            "vehicle_number":        vn,
            "vehicle_name":          r[1],
            "current_location":      current_loc,
            "speed":                 speed,
            "current_fuel":          current_fuel,
            "fuel_capacity":         fuel_capacity,
            "fuel_consumption_rate": consumption_rate,
            "max_load_capacity":     max_load,
            "avail_windows":         avail_windows,
        }

        ok = is_vehicle_available_reachable_fuelled(
            candidate, trip_start_loc, trip_end_loc,
            actual_start, actual_end, base_t0
        )
        if not ok:
            continue

        fuel_cost = compute_vehicle_fuel_cost(
            current_loc, trip_start_loc, trip_end_loc,
            current_fuel, fuel_capacity, consumption_rate, speed
        )
        candidate["fuel_cost"] = fuel_cost
        candidates.append(candidate)

    return candidates


# ─────────────────────────────────────────────
# CHECKS
# ─────────────────────────────────────────────

def is_vehicle_available_reachable_fuelled(
    candidate, trip_start_loc, end_loc,
    actual_start, actual_end, base_t0
):
    avail_windows    = candidate["avail_windows"]
    current_loc      = candidate["current_location"]
    speed            = candidate["speed"]
    current_fuel     = candidate["current_fuel"]
    fuel_capacity    = candidate["fuel_capacity"]
    consumption_rate = candidate["fuel_consumption_rate"]

    # 1. Availability
    conflict, _ = overlaps_availability(base_t0, actual_end, avail_windows)
    if conflict:
        return False

    # 2. Fuel check
    fuel_conflict = check_vehicle_fuel(
        current_loc, trip_start_loc, end_loc,
        current_fuel, fuel_capacity, consumption_rate,
        speed, base_t0, actual_start, actual_end,
        candidate["vehicle_number"], avail_windows
    )
    if fuel_conflict:
        return False

    # 3. Reachability
    if current_loc == trip_start_loc:
        return True

    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None or dist == 0:
        return dist is not None

    travel_secs = travel_time_secs(dist, speed)
    depart_time = base_t0 - timedelta(seconds=travel_secs)

    travel_conflict, _ = overlaps_availability(depart_time, base_t0, avail_windows)
    if travel_conflict:
        return False

    return True


def is_individual_available_reachable(
    candidate, trip_start_loc,
    actual_start, actual_end, base_t0
):
    avail_windows = candidate["avail_windows"]
    current_loc   = candidate["current_location"]

    # 1. Availability
    conflict, _ = overlaps_availability(base_t0, actual_end, avail_windows)
    if conflict:
        return False

    # 2. Reachability
    if current_loc == trip_start_loc:
        return True

    dist = fetch_distance(current_loc, trip_start_loc)
    if dist is None or dist == 0:
        return dist is not None

    travel_secs = travel_time_secs(dist, INDIVIDUAL_SPEED_KMH)
    depart_time = base_t0 - timedelta(seconds=travel_secs)

    travel_conflict, _ = overlaps_availability(depart_time, base_t0, avail_windows)
    return not travel_conflict


# ─────────────────────────────────────────────
# FUEL COST
# ─────────────────────────────────────────────

def compute_vehicle_fuel_cost(
    current_loc, start_loc, end_loc,
    current_fuel, fuel_capacity, consumption_rate, speed
):
    dist_to_start  = fetch_distance(current_loc, start_loc) or 0.0
    dist_start_end = fetch_distance(start_loc, end_loc)     or 0.0
    fuel_to_start  = fuel_needed(dist_to_start, consumption_rate)
    buffer_fuel    = fuel_needed(100.0, consumption_rate)
    total_dist     = dist_to_start + dist_start_end

    if current_fuel >= fuel_to_start + buffer_fuel:
        return fuel_needed(total_dist, consumption_rate)

    if fetch_location_has_fuel(current_loc):
        return fuel_needed(total_dist, consumption_rate)

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
        if current_fuel < fuel_needed(dist_to_station, consumption_rate):
            continue
        if fuel_capacity < (fuel_needed(dist_station_start, consumption_rate) + buffer_fuel):
            continue

        detour_dist = dist_to_station + dist_station_start
        if detour_dist < best_detour_dist:
            best_detour_dist = detour_dist

    if best_detour_dist == float("inf"):
        return float("inf")

    return fuel_needed(best_detour_dist + dist_start_end, consumption_rate)


# ─────────────────────────────────────────────
# OPTIMAL COMBO
# ─────────────────────────────────────────────

def find_optimal_vehicle_combo(
    original_vehicle_number, trip_start_loc, trip_end_loc,
    actual_start, actual_end, base_t0,
    assigned_vehicles, used_replacements_vehicles
):
    from itertools import combinations

    original_capacity = fetch_original_vehicle_capacity(original_vehicle_number)
    exclude           = assigned_vehicles | used_replacements_vehicles

    viable = fetch_any_capable_vehicles(
        exclude, original_capacity,
        trip_start_loc, trip_end_loc,
        base_t0, actual_start, actual_end
    )

    if not viable:
        return None, float("inf")

    best_combo = None
    best_fuel  = float("inf")

    for size in range(1, min(4, len(viable) + 1)):
        for combo in combinations(viable, size):
            total_capacity = sum(v["max_load_capacity"] for v in combo)
            if total_capacity < original_capacity:
                continue
            total_fuel = sum(v["fuel_cost"] for v in combo)
            if total_fuel < best_fuel:
                best_fuel  = total_fuel
                best_combo = list(combo)

    return best_combo, best_fuel


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def resolve_conflicts(conflicts, plan_id, trip_map, base_t0):
    assigned_vehicles, assigned_individuals = fetch_plan_assigned_resources(plan_id)

    used_replacements_vehicles    = set()
    used_replacements_individuals = set()

    resolutions = []

    for conflict in conflicts:
        trip_id    = conflict["trip_id"]
        identifier = conflict["identifier"]
        ctype      = conflict["conflict_type"]

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
        trip_end_loc   = trip.get("end_location_id")

        # ── Vehicle conflict ──
        if ctype == "Vehicle":

            # Step 1: same type
            candidates = fetch_same_type_vehicles(
                identifier,
                assigned_vehicles | used_replacements_vehicles
            )

            best      = None
            best_dist = float("inf")

            for candidate in candidates:
                ok = is_vehicle_available_reachable_fuelled(
                    candidate, trip_start_loc, trip_end_loc,
                    actual_start, actual_end, base_t0
                )
                if ok:
                    dist = fetch_distance(candidate["current_location"], trip_start_loc) or 0.0
                    if dist < best_dist:
                        best_dist = dist
                        best      = candidate

            if best:
                used_replacements_vehicles.add(best["vehicle_number"])
                resolutions.append({
                    "trip_id":          trip_id,
                    "original":         identifier,
                    "conflict_type":    "Vehicle",
                    "replacement":      best["vehicle_number"],
                    "replacement_name": best["vehicle_name"],
                    "resolved":         True,
                    "resolution_type":  "same_type",
                    "split":            False
                })

            else:
                # Step 2: any type, optimal fuel combo
                combo, total_fuel = find_optimal_vehicle_combo(
                    identifier, trip_start_loc, trip_end_loc,
                    actual_start, actual_end, base_t0,
                    assigned_vehicles, used_replacements_vehicles
                )

                if combo:
                    for v in combo:
                        used_replacements_vehicles.add(v["vehicle_number"])
                    resolutions.append({
                        "trip_id":          trip_id,
                        "original":         identifier,
                        "conflict_type":    "Vehicle",
                        "replacement":      [v["vehicle_number"] for v in combo],
                        "replacement_name": [v["vehicle_name"]   for v in combo],
                        "total_fuel_cost":  round(total_fuel, 2),
                        "resolved":         True,
                        "resolution_type":  "cross_type",
                        "split":            len(combo) > 1
                    })
                else:
                    resolutions.append({
                        "trip_id":          trip_id,
                        "original":         identifier,
                        "conflict_type":    "Vehicle",
                        "replacement":      None,
                        "resolved":         False,
                        "resolution_type":  "cross_type_failed"
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
                ok = is_individual_available_reachable(
                    candidate, trip_start_loc,
                    actual_start, actual_end, base_t0
                )
                if ok:
                    dist = fetch_distance(candidate["current_location"], trip_start_loc) or 0.0
                    if dist < best_dist:
                        best_dist = dist
                        best      = candidate

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