from flask import Blueprint, jsonify, request
from db import get_connection
from routes.feasible import run_scheduler, fetch_plan_data
from routes.resolver import resolve_conflicts

plans_bp = Blueprint('plans', __name__)


@plans_bp.route('/api/plans', methods=['GET'])
def get_plans():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT plan_id, plan_name, num_of_vehicles, default_start_time, total_fuel
        FROM plans
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    plans = []
    for row in rows:
        plans.append({
            "plan_id":            row[0],
            "plan_name":          row[1],
            "num_of_vehicles":    row[2],
            "default_start_time": str(row[3]),
            "total_fuel":         float(row[4])
        })
    return jsonify(plans)


@plans_bp.route('/api/plans/<int:plan_id>/trips', methods=['GET'])
def get_plan_trips(plan_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            t.trip_id,
            t.vehicle_number,
            v.vehicle_name,
            vt.type_name,
            r.start_location_id,
            l1.location_name  AS from_location,
            r.end_location_id,
            l2.location_name  AS to_location,
            r.distance,
            lt.load_type_name,
            t.quantity_of_load,
            t.start_offset,
            t.duration,
            u.unit_name
        FROM trips t
        JOIN vehicles      v  ON v.vehicle_number   = t.vehicle_number
        JOIN vehicle_types  vt ON vt.vehicle_type_id = v.vehicle_type_id
        JOIN routes        r  ON r.route_id          = t.route_id
        JOIN locations     l1 ON l1.location_id      = r.start_location_id
        JOIN locations     l2 ON l2.location_id      = r.end_location_id
        JOIN load_types    lt ON lt.load_type_id     = t.load_type_id
        JOIN units         u  ON u.unit_id           = t.unit_id
        WHERE t.plan_id = %s
        ORDER BY t.start_offset
    """, (plan_id,))
    trips = cur.fetchall()

    result = []
    for trip in trips:
        trip_id = trip[0]
        cur2 = conn.cursor()
        cur2.execute("""
            SELECT i.individual_id, i.name, ct.crew_type_name
            FROM trip_crew   tc
            JOIN individuals  i  ON i.individual_id  = tc.individual_id
            JOIN crew_types   ct ON ct.crew_type_id  = i.crew_type_id
            WHERE tc.trip_id = %s
        """, (trip_id,))
        crew = cur2.fetchall()
        cur2.close()

        result.append({
            "trip_id":        trip[0],
            "vehicle_number": trip[1],
            "vehicle_name":   trip[2],
            "vehicle_type":   trip[3],
            "from_location":  trip[5],
            "to_location":    trip[7],
            "distance_km":    float(trip[8]),
            "load_type":      trip[9],
            "quantity":       float(trip[10]),
            "start_offset":   str(trip[11]),
            "duration":       str(trip[12]),
            "unit":           trip[13],
            "crew": [
                {"id": c[0], "name": c[1], "role": c[2]}
                for c in crew
            ]
        })

    cur.close()
    conn.close()
    return jsonify(result)


def fetch_trips_for_resolution(plan_id):
    """Fetch trips with crew for resolver's trip_map."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.trip_id, r.start_location_id
        FROM trips t
        JOIN routes r ON r.route_id = t.route_id
        WHERE t.plan_id = %s
    """, (plan_id,))
    trip_rows = cur.fetchall()

    trips = []
    for row in trip_rows:
        trip_id = row[0]
        cur.execute("""
            SELECT i.individual_id, i.name, i.current_location_id
            FROM trip_crew tc
            JOIN individuals i ON i.individual_id = tc.individual_id
            WHERE tc.trip_id = %s
        """, (trip_id,))
        crew = cur.fetchall()
        trips.append({
            "trip_id":           row[0],
            "start_location_id": row[1],
            "crew": [
                {"individual_id": c[0], "name": c[1], "current_location_id": c[2]}
                for c in crew
            ]
        })

    cur.close()
    conn.close()
    return trips


@plans_bp.route('/api/plans/feasibility', methods=['POST'])
def check_feasibility():
    data    = request.json
    plan_id = data['plan_id']
    date    = data['date']
    time    = data.get('time')

    result = run_scheduler(plan_id, date, time)

    resolutions = []
    if not result["feasible"] and result["conflicts"]:
        base_t0, _ = fetch_plan_data(plan_id, date, time)
        resolutions = resolve_conflicts(
            result["conflicts"],
            plan_id,
            {t["trip_id"]: t for t in fetch_trips_for_resolution(plan_id)},
            base_t0
        )

    for c in result["conflicts"]:
        for key in ("not_available_from", "not_available_to", "actual_start", "actual_end", "earliest_available"):
            val = c.get(key)
            if val is not None and not isinstance(val, str):
                c[key] = str(val)

    return jsonify({
        "feasible":    result["feasible"],
        "schedule":    result["schedule"],
        "conflicts":   result["conflicts"],
        "resolutions": resolutions
    })