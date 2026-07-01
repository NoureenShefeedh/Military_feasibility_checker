"""
save_scheduled_run.py
─────────────────────
Persists the output of run_scheduler() + resolve_conflicts() into the
scheduled_runs and scheduled_run_trips tables.

Also inserts into individual_availability and vehicle_availability to mark
each crew member and vehicle as unavailable for the duration of their trips.

Public API
----------
save_scheduled_run(plan_id, date_str, schedule, trip_map, resolutions)
    → { "run_id": int, "trips_saved": int }

can_commit_run(conflicts, resolutions)
    → bool   (True = all conflicts have a valid resolution, safe to commit)
"""

from datetime import datetime
from db import get_connection


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _build_resolution_index(resolutions: list) -> dict:
    """
    Build a lookup dict  trip_id → resolution  from the resolutions list
    returned by resolve_conflicts().

    Only resolutions where resolved=True are kept — unresolved ones should
    block the commit entirely (enforced by can_commit_run before we get here).
    """
    index = {}
    for r in resolutions:
        if not r.get("resolved"):
            continue
        tid = r["trip_id"]
        index.setdefault(tid, {})
        ctype = r.get("conflict_type")
        index[tid][ctype] = r
    return index


def _fetch_original_crew(trip_id: int, cur) -> list[int]:
    """Return the list of individual_ids from trip_crew for a given trip."""
    cur.execute(
        "SELECT individual_id FROM trip_crew WHERE trip_id = %s ORDER BY individual_id",
        (trip_id,)
    )
    return [row[0] for row in cur.fetchall()]


def _fetch_individual_id_by_name(name: str, cur) -> int | None:
    """Resolve an individual's name to their ID.  Returns None if not found."""
    cur.execute(
        "SELECT individual_id FROM individuals WHERE name = %s LIMIT 1",
        (name,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def _resolve_vehicle(trip_id: int, original_vehicle: str, resolution_index: dict) -> str:
    """
    Return the vehicle_number to record for this trip.

    Rules
    -----
    • If there is a resolved Vehicle conflict for this trip, use the
      replacement vehicle number.
    • For multi-vehicle strategies (replacement is a list) we take the
      first vehicle in the list — the primary carrier.
    • If no conflict / unresolved, fall back to the original vehicle.
    """
    res = resolution_index.get(trip_id, {}).get("Vehicle")
    if not res:
        return original_vehicle

    replacement = res.get("replacement")
    if isinstance(replacement, list):
        return replacement[0] if replacement else original_vehicle
    if isinstance(replacement, str):
        return replacement
    return original_vehicle


def _resolve_individual_ids(trip_id: int, original_ids: list[int],
                             resolution_index: dict, cur) -> list[int]:
    """
    Return the final list of individual_ids to record for this trip.
    Swaps out conflicted crew members for their replacements.
    """
    substitutions: dict[str, str] = {}
    for res in resolution_index.get(trip_id, {}).values():
        if res.get("conflict_type") != "Individual":
            continue
        orig_name    = res.get("original")
        replace_name = res.get("replacement")
        if orig_name and replace_name and orig_name != replace_name:
            substitutions[orig_name] = replace_name

    if not substitutions:
        return original_ids

    cur.execute("""
        SELECT tc.individual_id, i.name
        FROM trip_crew tc
        JOIN individuals i ON i.individual_id = tc.individual_id
        WHERE tc.trip_id = %s
    """, (trip_id,))
    crew_rows = {row[1]: row[0] for row in cur.fetchall()}

    result = list(original_ids)
    for orig_name, replacement_name in substitutions.items():
        orig_id = crew_rows.get(orig_name)
        if orig_id is None:
            continue
        repl_id = _fetch_individual_id_by_name(replacement_name, cur)
        if repl_id is None:
            continue
        result = [repl_id if iid == orig_id else iid for iid in result]

    return result


# ─────────────────────────────────────────────
# AVAILABILITY HELPERS
# ─────────────────────────────────────────────

def _insert_individual_availability(
    individual_id: int,
    busy_start: datetime,
    busy_end: datetime,
    reason: str,
    cur,
) -> None:
    """
    Insert a row into individual_availability marking the person unavailable
    for the window [busy_start, busy_end].

    Schema: availability_id (serial PK), individual_id, reason,
            not_available_from, not_available_to
    """
    cur.execute("""
        INSERT INTO public.individual_availability
            (individual_id, reason, not_available_from, not_available_to)
        VALUES (%s, %s, %s, %s)
    """, (individual_id, reason, busy_start, busy_end))


def _insert_vehicle_availability(
    vehicle_number: str,
    busy_start: datetime,
    busy_end: datetime,
    reason: str,
    cur,
) -> None:
    """
    Insert a row into vehicle_availability marking the vehicle unavailable
    for the window [busy_start, busy_end].

    Schema: availability_id (serial PK), vehicle_number, reason,
            not_available_from, not_available_to
    """
    cur.execute("""
        INSERT INTO public.vehicle_availability
            (vehicle_number, reason, not_available_from, not_available_to)
        VALUES (%s, %s, %s, %s)
    """, (vehicle_number, reason, busy_start, busy_end))


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def can_commit_run(conflicts: list, resolutions: list) -> bool:
    """
    Return True only if every detected conflict has a successful resolution.
    """
    if not conflicts:
        return True

    resolved_trip_ids = {
        r["trip_id"]
        for r in resolutions
        if r.get("resolved") is True
    }

    conflicted_trip_ids = {c["trip_id"] for c in conflicts}
    return conflicted_trip_ids.issubset(resolved_trip_ids)


def save_scheduled_run(
    plan_id: int,
    date_str: str,              # "YYYY-MM-DD"
    schedule: list,             # run_scheduler() → "schedule" list
    trip_map: dict,             # trip_id → trip dict (from fetch_plan_data)
    resolutions: list,          # resolve_conflicts() → "resolutions" list
) -> dict:
    """
    Persist a committed run to the database.

    Steps
    -----
    1. Clear availability rows for any existing run on this plan + date.
    2. Delete any existing scheduled_run for this plan_id + run_date
       (cascade deletes its scheduled_run_trips automatically).
    3. Insert a new scheduled_runs header row.
    4. For each trip in `schedule`:
         a. Determine final vehicle_number (original or replacement).
         b. Determine final individual_ids (original or substituted).
         c. Insert into scheduled_run_trips.
         d. Insert into individual_availability for every crew member.
         e. Insert into vehicle_availability for the assigned vehicle.

    Returns
    -------
    { "run_id": int, "trips_saved": int }
    """
    resolution_index = _build_resolution_index(resolutions)
    run_date         = datetime.strptime(date_str, "%Y-%m-%d").date()
    conn             = get_connection()
    cur              = conn.cursor()

    try:
        # ── Fetch plan name for availability reason label ──────────────────
        cur.execute("SELECT plan_name FROM public.plans WHERE plan_id = %s", (plan_id,))
        row = cur.fetchone()
        plan_name = row[0] if row else f"Plan {plan_id}"
        reason = f"Assigned to {plan_name}"

        # ── Step 1: clear availability rows for the run being replaced ──
        cur.execute("""
            SELECT run_id FROM public.scheduled_runs
            WHERE plan_id = %s AND run_date = %s
            LIMIT 1
        """, (plan_id, run_date))
        existing = cur.fetchone()
        if existing:
            old_run_id = existing[0]
            cur.execute("DELETE FROM public.individual_availability WHERE reason = %s", (reason,))
            cur.execute("DELETE FROM public.vehicle_availability WHERE reason = %s", (reason,))

        # ── Step 2: delete existing run header (cascade kills trip rows) ──
        cur.execute("""
            DELETE FROM public.scheduled_runs
            WHERE plan_id = %s AND run_date = %s
        """, (plan_id, run_date))

        # ── Step 3: insert new header row ─────────────────────────────────
        cur.execute("""
            INSERT INTO public.scheduled_runs (plan_id, run_date, created_at)
            VALUES (%s, %s, NOW())
            RETURNING run_id
        """, (plan_id, run_date))
        run_id = cur.fetchone()[0]

        # ── Step 3: insert one trip row + availability per trip ────────────
        trips_saved = 0
        for entry in schedule:
            trip_id      = entry["trip_id"]
            actual_start = entry["actual_start"]
            actual_end   = entry["actual_end"]

            if isinstance(actual_start, str):
                actual_start = datetime.fromisoformat(actual_start)
            if isinstance(actual_end, str):
                actual_end = datetime.fromisoformat(actual_end)

            trip = trip_map.get(trip_id)
            if not trip:
                raise ValueError(
                    f"trip_id {trip_id} found in schedule but missing from trip_map"
                )

            original_vehicle = trip["vehicle_number"]
            original_ids     = _fetch_original_crew(trip_id, cur)

            final_vehicle = _resolve_vehicle(trip_id, original_vehicle, resolution_index)
            final_ids     = _resolve_individual_ids(trip_id, original_ids, resolution_index, cur)

            # 3a. Persist the scheduled trip row.
            cur.execute("""
                INSERT INTO public.scheduled_run_trips
                    (run_id, trip_id, actual_start, actual_end, vehicle_number, individual_ids)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (run_id, trip_id, actual_start, actual_end, final_vehicle, final_ids))

            # 3b. Mark every crew member unavailable for this trip's window.
            for individual_id in final_ids:
                _insert_individual_availability(
                    individual_id=individual_id,
                    busy_start=actual_start,
                    busy_end=actual_end,
                    reason=reason,
                    cur=cur,
                )

            # 3c. Mark the vehicle unavailable for this trip's window.
            _insert_vehicle_availability(
                vehicle_number=final_vehicle,
                busy_start=actual_start,
                busy_end=actual_end,
                reason=reason,
                cur=cur,
            )

            trips_saved += 1

        conn.commit()
        return {"run_id": run_id, "trips_saved": trips_saved}

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()
