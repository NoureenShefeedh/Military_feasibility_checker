from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from db import get_connection
from routes.feasible import run_scheduler, fetch_plan_data
from routes.resolver import resolve_conflicts
from routes.save_scheduled_run import save_scheduled_run, can_commit_run

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


# ── Moved to /api/feasibility to avoid colliding with /<int:plan_id> routes ──
@plans_bp.route('/api/feasibility', methods=['POST'])
def check_feasibility():
    data    = request.json
    plan_id = data['plan_id']
    date    = data['date']
    time    = data.get('time')

    result = run_scheduler(plan_id, date, time)

    resolutions = {"resolutions": [], "next_feasible_times": []}

    if not result["feasible"] and result["conflicts"]:
        base_t0, trips = fetch_plan_data(plan_id, date, time)
        trip_map = {t["trip_id"]: t for t in trips}

        resolutions = resolve_conflicts(
            result["conflicts"],
            plan_id,
            trip_map,
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


@plans_bp.route('/api/plans/<int:plan_id>/can-commit', methods=['POST'])
def check_can_commit(plan_id):
    data        = request.get_json(force=True) or {}
    conflicts   = data.get("conflicts",   [])
    resolutions = data.get("resolutions", [])
    date_str    = data.get("date")

    committable = can_commit_run(conflicts, resolutions)

    run_id_exists = False
    if date_str:
        try:
            run_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("""
                SELECT 1 FROM public.scheduled_runs
                WHERE plan_id = %s AND run_date = %s
                LIMIT 1
            """, (plan_id, run_date))
            run_id_exists = cur.fetchone() is not None
            cur.close()
            conn.close()
        except Exception:
            pass

    return jsonify({
        "can_commit":    committable,
        "run_id_exists": run_id_exists,
    })


@plans_bp.route('/api/plans/<int:plan_id>/commit-feasible', methods=['POST'])
def commit_feasible_run(plan_id):
    """
    Commits the run using each conflicted trip's next feasible start time
    (original vehicle + crew, no replacements).
    Non-conflicted trips run at their normal base_t0 + start_offset time.

    Body: {
        "date": "YYYY-MM-DD",
        "time": "HH:MM",                         (optional)
        "next_feasible_times": [                  // from /feasibility response
            { "trip_id": 1, "feasible_start": "...", "feasible_end": "..." },
            ...
        ]
    }

    Returns: { "run_id": int, "trips_saved": int }  → HTTP 201
    """
    from datetime import timedelta

    data              = request.get_json(force=True) or {}
    date_str          = data.get("date")
    time_str          = data.get("time", "")
    next_feasible     = data.get("next_feasible_times", [])

    if not date_str:
        return jsonify({"error": "date is required"}), 400

    # Build a lookup of trip_id → feasible_start/end for conflicted trips.
    feasible_map = {}
    for ft in next_feasible:
        tid = ft.get("trip_id")
        fs  = ft.get("feasible_start")
        fe  = ft.get("feasible_end")
        if tid and fs and fe:
            feasible_map[tid] = {
                "actual_start": datetime.fromisoformat(fs),
                "actual_end":   datetime.fromisoformat(fe),
            }

    # Re-run scheduler to get base_t0 and the full trip list.
    result   = run_scheduler(plan_id, date_str, time_str)
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    base_t0, trips = fetch_plan_data(plan_id, date_str, time_str)
    trip_map       = {t["trip_id"]: t for t in trips}

    # Build a custom schedule: conflicted trips use feasible times,
    # all others use their normal base_t0 + start_offset.
    schedule = []
    for trip in trips:
        tid = trip["trip_id"]
        if tid in feasible_map:
            schedule.append({
                "trip_id":      tid,
                "actual_start": feasible_map[tid]["actual_start"].isoformat(),
                "actual_end":   feasible_map[tid]["actual_end"].isoformat(),
            })
        else:
            actual_start = base_t0 + timedelta(seconds=trip["start_offset_secs"])
            actual_end   = actual_start + timedelta(seconds=trip["duration_secs"])
            schedule.append({
                "trip_id":      tid,
                "actual_start": actual_start.isoformat(),
                "actual_end":   actual_end.isoformat(),
            })

    # Save with no resolutions — original vehicle + crew for every trip.
    try:
        saved = save_scheduled_run(
            plan_id     = plan_id,
            date_str    = date_str,
            schedule    = schedule,
            trip_map    = trip_map,
            resolutions = [],
        )
        return jsonify(saved), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@plans_bp.route('/api/plans/<int:plan_id>/commit', methods=['POST'])
def commit_scheduled_run(plan_id):
    data     = request.get_json(force=True) or {}
    date_str = data.get("date")
    time_str = data.get("time", "")

    if not date_str:
        return jsonify({"error": "date is required"}), 400

    result = run_scheduler(plan_id, date_str, time_str)

    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    schedule  = result.get("schedule", [])
    conflicts = result.get("conflicts", [])

    base_t0, trips = fetch_plan_data(plan_id, date_str, time_str)
    trip_map       = {t["trip_id"]: t for t in trips}

    resolutions = []
    if conflicts:
        resolved    = resolve_conflicts(conflicts, plan_id, trip_map, base_t0)
        resolutions = resolved.get("resolutions", [])

        if not can_commit_run(conflicts, resolutions):
            return jsonify({
                "error":   "Cannot commit — one or more conflicts have no valid resolution.",
                "details": resolutions,
            }), 409

    try:
        saved = save_scheduled_run(
            plan_id     = plan_id,
            date_str    = date_str,
            schedule    = schedule,
            trip_map    = trip_map,
            resolutions = resolutions,
        )
        return jsonify(saved), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@plans_bp.route('/api/plans/<int:plan_id>/scheduled-run', methods=['GET'])
def get_scheduled_run(plan_id):
    from collections import Counter

    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "date is required"}), 400

    try:
        run_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400

    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT run_id, created_at FROM public.scheduled_runs
                WHERE plan_id = %s AND run_date = %s
                LIMIT 1
            """, (plan_id, run_date))
            row = cur.fetchone()
            if not row:
                return jsonify({"exists": False})

            run_id, created_at = row

            # NOTE: added t.start_offset here so we can derive the run's
            # committed base time below (see committed_time calculation).
            cur.execute("""
                SELECT
                    srt.trip_id, srt.actual_start, srt.actual_end,
                    srt.vehicle_number, v.vehicle_name,
                    srt.individual_ids, srt.resolution_data,
                    r.start_location_id, l1.location_name,
                    r.end_location_id,   l2.location_name,
                    t.start_offset
                FROM public.scheduled_run_trips srt
                JOIN public.vehicles  v  ON v.vehicle_number = srt.vehicle_number
                JOIN public.trips     t  ON t.trip_id         = srt.trip_id
                JOIN public.routes    r  ON r.route_id         = t.route_id
                JOIN public.locations l1 ON l1.location_id     = r.start_location_id
                JOIN public.locations l2 ON l2.location_id     = r.end_location_id
                WHERE srt.run_id = %s
                ORDER BY srt.actual_start
            """, (run_id,))
            trip_rows = cur.fetchall()

            trips = []
            base_t0_candidates = []

            for (tid, astart, aend, vn, vname, iids, resolution_data,
                 start_loc_id, start_loc_name, end_loc_id, end_loc_name,
                 start_offset) in trip_rows:

                crew_names = []
                if iids:
                    cur.execute("""
                        SELECT name FROM public.individuals
                        WHERE individual_id = ANY(%s)
                    """, (iids,))
                    crew_names = [r[0] for r in cur.fetchall()]

                # Derive this trip's implied base_t0 = actual_start - start_offset.
                # For trips that ran at their normal (unshifted) time, this
                # equals the true committed base time. Trips that were shifted
                # to a "next feasible start" will disagree — that's expected,
                # they're outliers, not the majority.
                offset_secs = (
                    start_offset.hour * 3600 +
                    start_offset.minute * 60 +
                    start_offset.second
                )
                candidate_base_t0 = astart - timedelta(seconds=offset_secs)
                base_t0_candidates.append(candidate_base_t0)

                trips.append({
                    "trip_id":         tid,
                    "actual_start":    astart.isoformat(),
                    "actual_end":      aend.isoformat(),
                    "vehicle_number":  vn,
                    "vehicle_name":    vname,
                    "crew":            crew_names,
                    "from_location":   start_loc_name,
                    "to_location":     end_loc_name,
                    "resolution_data": resolution_data or {},
                })
        finally:
            cur.close()
    finally:
        conn.close()

    # Majority vote across trips to find the actual committed base time.
    committed_time_str = None
    if base_t0_candidates:
        counts = Counter(base_t0_candidates)
        most_common_base_t0, _ = counts.most_common(1)[0]
        committed_time_str = most_common_base_t0.strftime("%H:%M")

    return jsonify({
        "exists":         True,
        "run_id":         run_id,
        "created_at":     created_at.isoformat(),
        "committed_time": committed_time_str,   # "HH:MM" — NEW
        "trips":          trips,
    })