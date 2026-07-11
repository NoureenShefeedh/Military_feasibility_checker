"""
save_scheduled_run.py
─────────────────────
Persists the output of run_scheduler() + resolve_conflicts() into the
scheduled_runs and scheduled_run_trips tables.

Also inserts into individual_availability and vehicle_availability to mark
each crew member and vehicle as unavailable for the duration of their trips.

Two things this file is careful to get right about those availability
windows:

1. DEADHEAD TRAVEL TIME. A vehicle/individual isn't "free" until they've
   actually made it back from wherever the trip took them -- and they
   weren't free before the trip either, the moment they set off from
   their current location to REACH the trip's start point. So busy_start
   is pushed back by however long that trip to the start location takes,
   not just set to the trip's own actual_start.

2. ROUND TRIPS. For a round-trip resolution, the vehicle is busy from
   when it sets off for round 1 all the way through when it finishes the
   LAST round -- not just its first leg. That full span lives in the
   resolution's "rounds" data, not in actual_start/actual_end.

If a trip's resolution came from POACHING a resource off a lower-priority
plan, this also removes that source plan's now-stale availability row for
the same vehicle/individual + time window -- otherwise the same resource
ends up "unavailable" for two different plans at the same time, and the
source plan's future feasibility checks would incorrectly still think it
owns a resource it no longer has.

3. RESOLUTION DATA. Each trip's full resolution snapshot (which strategy
   was used, replacement resources, and for round trips every round's
   depart/arrive time) is saved into scheduled_run_trips.resolution_data
   (JSONB) at commit time. This is what lets the committed-run view later
   show exactly what happened for each trip -- including round-by-round
   timing -- without having to re-run the resolver.

Public API
----------
save_scheduled_run(plan_id, date_str, schedule, trip_map, resolutions)
    → { "run_id": int, "trips_saved": int }

can_commit_run(conflicts, resolutions)
    → bool   (True = all conflicts have a valid resolution, safe to commit)
"""

from datetime import datetime, timedelta
from psycopg2.extras import Json
from db import get_connection
from routes.feasible import fetch_distance, travel_time_secs, INDIVIDUAL_SPEED_KMH


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


def _parse_dt(value):
    """Parse an ISO datetime string. Passes datetimes through unchanged."""
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


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
    • For a poach ("poached_from_lower_priority_plan"), replacement equals
      the original vehicle number, so this naturally returns the same
      vehicle — the poach doesn't change WHICH vehicle is on the trip,
      only who's allowed to keep it. Cleanup of the source plan's stale
      availability row is handled separately (see save_scheduled_run).
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

    Note: a poach resolution has original == replacement (same person,
    just reclaimed from a lower-priority plan), so the substitution loop
    below naturally skips it and the original ID is kept as-is — correct,
    since the person on the trip doesn't change.
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
# DEADHEAD TRAVEL HELPERS
# ─────────────────────────────────────────────

def _fetch_vehicle_location_and_speed(vehicle_number: str, cur):
    """Look up a vehicle's current parking location and its type's speed."""
    cur.execute("""
        SELECT v.current_location_id, vt.default_speed
        FROM vehicles v
        JOIN vehicle_types vt ON vt.vehicle_type_id = v.vehicle_type_id
        WHERE v.vehicle_number = %s
    """, (vehicle_number,))
    row = cur.fetchone()
    if not row:
        return None, None
    return row[0], (float(row[1]) if row[1] is not None else None)


def _fetch_individual_location(individual_id: int, cur):
    """Look up a crew member's current location."""
    cur.execute(
        "SELECT current_location_id FROM individuals WHERE individual_id = %s",
        (individual_id,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def _vehicle_deadhead_secs(vehicle_number: str, trip_start_loc, cur) -> int:
    """
    Travel time (seconds) for this vehicle to get from wherever it's
    currently parked to the trip's start location. Returns 0 if it's
    already there, or if location/distance data is missing — fails safe
    (under-blocks rather than blocking the save on bad data) rather than
    raising, since this is a best-effort padding of the busy window.
    """
    location, speed = _fetch_vehicle_location_and_speed(vehicle_number, cur)
    if location is None or speed is None or location == trip_start_loc:
        return 0
    dist = fetch_distance(location, trip_start_loc)
    if not dist:
        return 0
    return travel_time_secs(dist, speed)


def _individual_deadhead_secs(individual_id: int, trip_start_loc, cur) -> int:
    """Same idea as _vehicle_deadhead_secs, for a crew member's own commute."""
    location = _fetch_individual_location(individual_id, cur)
    if location is None or location == trip_start_loc:
        return 0
    dist = fetch_distance(location, trip_start_loc)
    if not dist:
        return 0
    return travel_time_secs(dist, INDIVIDUAL_SPEED_KMH)


# ─────────────────────────────────────────────
# BUSY-WINDOW RESOLUTION
# ─────────────────────────────────────────────

def _resolve_vehicle_busy_windows(
    trip_id: int,
    trip_start_loc,
    final_vehicle: str,
    actual_start: datetime,
    actual_end: datetime,
    resolution_index: dict,
    cur,
) -> list[tuple[str, datetime, datetime]]:
    """
    Return [(vehicle_number, busy_start, busy_end), ...] — one entry per
    vehicle that needs a vehicle_availability row for this trip, each with
    the FULL window that vehicle is actually occupied:

    • Non-round-trip cases (plain trip, same-type swap, poach, or a
      single-pass combo): busy_start is actual_start minus however long it
      takes this vehicle to travel from where it currently sits to the
      trip's start location — it's busy from the moment it sets off, not
      just once it arrives. busy_end is actual_end.

    • Round-trip cases: the resolver's own math (see
      find_best_single_vehicle_round_trips in resolve_conflicts.py)
      already assumes the vehicle departs its current location right at
      actual_start and arrives dh_secs later — so actual_start IS already
      the deadhead-inclusive departure point, no further subtraction
      needed. What actual_end doesn't capture is that the vehicle keeps
      going: busy_end must reach all the way to the LAST round's
      arrive_end, not the trip's own actual_end or the first round alone.
      For a combo round-trip, each vehicle has its own separate set of
      rounds and therefore its own busy window.
    """
    res = resolution_index.get(trip_id, {}).get("Vehicle")
    resolution_type = res.get("resolution_type") if res else None

    # ── Single vehicle running multiple round trips ──
    if resolution_type == "single_vehicle_round_trips":
        rounds = res.get("rounds") or []
        if rounds:
            busy_end = _parse_dt(rounds[-1]["arrive_end"])
            return [(final_vehicle, actual_start, busy_end)]
        return [(final_vehicle, actual_start, actual_end)]

    # ── Load split across multiple vehicles, each doing round trips ──
    if resolution_type == "multi_vehicle_combo_round_trips":
        rounds_by_vehicle = res.get("rounds") or {}
        windows = []
        for vn, info in rounds_by_vehicle.items():
            v_rounds = info.get("rounds") or []
            if not v_rounds:
                continue
            busy_end = _parse_dt(v_rounds[-1]["arrive_end"])
            windows.append((vn, actual_start, busy_end))
        if windows:
            return windows
        return [(final_vehicle, actual_start, actual_end)]

    # ── Load split across multiple vehicles, single pass (no round trips) ──
    if resolution_type == "multi_vehicle_combo":
        replacement = res.get("replacement") or [final_vehicle]
        windows = []
        for vn in replacement:
            dh_secs = _vehicle_deadhead_secs(vn, trip_start_loc, cur)
            busy_start = actual_start - timedelta(seconds=dh_secs)
            windows.append((vn, busy_start, actual_end))
        return windows

    # ── Same-type swap, poach, or no conflict at all: one vehicle ──
    dh_secs = _vehicle_deadhead_secs(final_vehicle, trip_start_loc, cur)
    busy_start = actual_start - timedelta(seconds=dh_secs)
    return [(final_vehicle, busy_start, actual_end)]


def _resolve_individual_busy_windows(
    trip_start_loc,
    final_ids: list[int],
    actual_start: datetime,
    actual_end: datetime,
    cur,
) -> list[tuple[int, datetime, datetime]]:
    """
    Return [(individual_id, busy_start, busy_end), ...] with each person's
    busy_start pushed back to cover their own travel time to the trip's
    start location — same reasoning as the vehicle version. Individuals
    don't do round trips in this system, so busy_end is always actual_end.
    """
    windows = []
    for individual_id in final_ids:
        dh_secs = _individual_deadhead_secs(individual_id, trip_start_loc, cur)
        busy_start = actual_start - timedelta(seconds=dh_secs)
        windows.append((individual_id, busy_start, actual_end))
    return windows


# ─────────────────────────────────────────────
# AVAILABILITY INSERT / DELETE HELPERS
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


def _delete_poached_vehicle_availability(
    vehicle_number: str,
    blocking_plan_name: str,
    busy_start: datetime,
    busy_end: datetime,
    cur,
) -> None:
    """
    Remove the SOURCE (lower-priority) plan's stale vehicle_availability row
    for a vehicle we just poached from it.

    Only deletes rows that:
      1. Belong to that specific vehicle,
      2. Were created with reason = "Assigned to <blocking_plan_name>", and
      3. Overlap the window we're now claiming.

    Point 3 matters: the source plan might have other, unrelated
    assignments for this same vehicle at different times — we must not
    touch those.
    """
    source_reason = f"Assigned to {blocking_plan_name}"
    cur.execute("""
        DELETE FROM public.vehicle_availability
        WHERE vehicle_number = %s
          AND reason = %s
          AND not_available_from < %s
          AND not_available_to > %s
    """, (vehicle_number, source_reason, busy_end, busy_start))


def _delete_poached_individual_availability(
    individual_id: int,
    blocking_plan_name: str,
    busy_start: datetime,
    busy_end: datetime,
    cur,
) -> None:
    """
    Same idea as _delete_poached_vehicle_availability, but for a poached
    crew member's individual_availability row.
    """
    source_reason = f"Assigned to {blocking_plan_name}"
    cur.execute("""
        DELETE FROM public.individual_availability
        WHERE individual_id = %s
          AND reason = %s
          AND not_available_from < %s
          AND not_available_to > %s
    """, (individual_id, source_reason, busy_end, busy_start))


def _cleanup_poached_source_availability(
    trip_id: int,
    vehicle_windows: list[tuple[str, datetime, datetime]],
    individual_windows: list[tuple[int, datetime, datetime]],
    resolution_index: dict,
    cur,
) -> None:
    """
    If this trip's Vehicle and/or Individual conflict was resolved by
    poaching from a lower-priority plan, strip out that source plan's
    stale availability row for the poached resource so it doesn't end up
    double-booked (once under the old plan's reason, once under ours).

    Uses the SAME busy windows we're about to insert (deadhead-adjusted),
    so the overlap check lines up with what we're actually claiming now,
    not just the trip's bare actual_start/actual_end.
    """
    trip_resolutions = resolution_index.get(trip_id, {})

    vehicle_res = trip_resolutions.get("Vehicle")
    if vehicle_res and vehicle_res.get("resolution_type") == "poached_from_lower_priority_plan":
        blocking_plan = vehicle_res.get("poached_from_plan")
        if blocking_plan and vehicle_windows:
            vn, busy_start, busy_end = vehicle_windows[0]
            _delete_poached_vehicle_availability(
                vn, blocking_plan, busy_start, busy_end, cur
            )

    individual_res = trip_resolutions.get("Individual")
    if individual_res and individual_res.get("resolution_type") == "poached_from_lower_priority_plan":
        blocking_plan = individual_res.get("poached_from_plan")
        # Poach resolutions don't carry individual_id, only the name
        # (original == replacement for a poach — same person, reclaimed).
        poached_name = individual_res.get("original")
        if blocking_plan and poached_name:
            poached_id = _fetch_individual_id_by_name(poached_name, cur)
            if poached_id is not None:
                match = next((w for w in individual_windows if w[0] == poached_id), None)
                if match:
                    _, busy_start, busy_end = match
                    _delete_poached_individual_availability(
                        poached_id, blocking_plan, busy_start, busy_end, cur
                    )


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
         c. Work out each resource's TRUE busy window — including travel
            time to reach the start location, and for round trips, the
            full span through the last round.
         d. If either resource was POACHED from a lower-priority plan,
            delete that source plan's now-stale availability row for it.
         e. Insert into scheduled_run_trips, including a JSONB snapshot of
            that trip's resolution (vehicle/individual replacement info
            and, for round trips, every round's depart/arrive time) so
            the committed-run view can show it later without re-running
            the resolver.
         f. Insert into individual_availability for every crew member.
         g. Insert into vehicle_availability for every assigned vehicle.

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

        # ── Step 4: insert one trip row + availability per trip ────────────
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

            trip_start_loc = trip.get("start_location_id")

            original_vehicle = trip["vehicle_number"]
            original_ids     = _fetch_original_crew(trip_id, cur)

            final_vehicle = _resolve_vehicle(trip_id, original_vehicle, resolution_index)
            final_ids     = _resolve_individual_ids(trip_id, original_ids, resolution_index, cur)

            # 4a. Work out each resource's true busy window: deadhead
            #     travel included at the start, and for round trips, the
            #     full span through the last round at the end.
            vehicle_windows = _resolve_vehicle_busy_windows(
                trip_id, trip_start_loc, final_vehicle,
                actual_start, actual_end, resolution_index, cur
            )
            individual_windows = _resolve_individual_busy_windows(
                trip_start_loc, final_ids, actual_start, actual_end, cur
            )

            # 4b. If this trip's resources were poached from a lower-priority
            #     plan, strip that plan's stale availability row first, so
            #     we don't end up with two overlapping "unavailable" windows
            #     for the same vehicle/individual.
            _cleanup_poached_source_availability(
                trip_id, vehicle_windows, individual_windows, resolution_index, cur
            )

            # 4c. Persist the scheduled trip row, including the resolution
            #     snapshot (vehicle/individual replacement + round-by-round
            #     timing for round trips) so it can be read back later.
            trip_resolution = resolution_index.get(trip_id, {})
            cur.execute("""
                INSERT INTO public.scheduled_run_trips
                    (run_id, trip_id, actual_start, actual_end,
                     vehicle_number, individual_ids, resolution_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                run_id, trip_id, actual_start, actual_end,
                final_vehicle, final_ids, Json(trip_resolution)
            ))

            # 4d. Mark every crew member unavailable for their true busy window.
            for individual_id, busy_start, busy_end in individual_windows:
                _insert_individual_availability(
                    individual_id=individual_id,
                    busy_start=busy_start,
                    busy_end=busy_end,
                    reason=reason,
                    cur=cur,
                )

            # 4e. Mark every assigned vehicle unavailable for its true busy window.
            for vehicle_number, busy_start, busy_end in vehicle_windows:
                _insert_vehicle_availability(
                    vehicle_number=vehicle_number,
                    busy_start=busy_start,
                    busy_end=busy_end,
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