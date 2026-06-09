# Military Plan Feasibility System

A web application for checking whether military operation plans can be executed on a given date, considering vehicle and personnel availability, travel times, and shared resource constraints.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Backend | Flask (Python) |
| Database | PostgreSQL |

---

## Project Structure

```
project/
  backend/
    app.py              # Flask app entry point
    db.py               # Database connection
    routes/
      plans.py          # API routes
      scheduler.py      # Core scheduling and feasibility logic
      resolver.py       # Conflict resolution engine
  frontend/
    src/
      pages/
        Plans.jsx         # Operation plans and trip details
        Feasibility.jsx   # Feasibility check interface
      components/
        TripCard.jsx        # Individual trip display
        ConflictTable.jsx   # Conflict and schedule display
        ResolutionTable.jsx # Replacement suggestions
      api/
        plans.js          # API calls
```

---

## Core Concepts

### Plans and Trips

A **plan** is a military operation with a default start time (T0). Each plan has multiple **trips** — individual vehicle movements between locations.

Trip timing is defined by:
- `start_offset` — how long after T0 loading and prep begins at the start location
- `duration` — how long the trip itself takes

So a trip's actual timeline on a given date is:
```
actual_start = T0 + start_offset
actual_end   = actual_start + duration
```

When a user provides a custom date and time, that becomes the new T0.

### Feasibility Check

A plan is feasible on a given date if every vehicle and crew member assigned to its trips is both **available** and **reachable** in time.

**Availability** is checked from T0 through actual_end — the resource must be free for the entire window from when the plan begins until their trip finishes.

**Reachability** works backwards — the resource must arrive at the trip's start location by T0 (so they're ready for loading). This means they must depart from their current location at `T0 - travel_time` and be free during that travel window.

### Shared Resources

If the same vehicle or crew member appears in multiple trips of the same plan, those trips must run sequentially — one after another. The system automatically detects this and finds the optimal ordering.

After completing one trip, the shared resource travels to the next trip's start location. The next trip cannot begin until the shared resource arrives. This arrival time may push the trip's actual start later than its offset would suggest.

The system uses **branch and bound** to find the ordering that finishes the plan earliest while keeping all resources available and reachable. If no conflict-free ordering exists, it returns the fastest possible ordering and reports exactly what conflicts remain.

### Conflict Resolution

When a plan is not feasible, the system suggests replacements for each conflicted resource:

- For a conflicted vehicle → finds another vehicle of the **same type** not already assigned to the plan, that is available from T0 through the trip end, and can physically travel from its current location to arrive by T0
- For a conflicted crew member → finds another individual of the **same crew type** under the same conditions

If no valid replacement exists, it reports that clearly.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/plans` | List all plans |
| GET | `/api/plans/<id>/trips` | Get all trips for a plan with vehicle, crew, load, and route details |
| POST | `/api/plans/feasibility` | Check if a plan is feasible on a given date |

### Feasibility Request

```json
{
  "plan_id": 2,
  "date": "2026-06-11",
  "time": "06:00"
}
```

`time` is optional — defaults to the plan's `default_start_time` if not provided.

### Feasibility Response

```json
{
  "feasible": false,
  "schedule": [
    {
      "trip_id": 4,
      "actual_start": "2026-06-11T06:10:00",
      "actual_end": "2026-06-11T11:10:00",
      "sequenced": false
    }
  ],
  "conflicts": [
    {
      "trip_id": 5,
      "identifier": "MH-TRK-002",
      "conflict_type": "Vehicle",
      "conflict_subtype": "unavailable",
      "reason": "Fuel Refill",
      "not_available_from": "2026-06-11T10:00:00",
      "not_available_to": "2026-06-11T13:00:00",
      "earliest_available": "2026-06-11T13:00:00",
      "actual_start": "2026-06-11T05:30:00",
      "actual_end": "2026-06-11T10:00:00"
    }
  ],
  "resolutions": [
    {
      "trip_id": 5,
      "original": "MH-TRK-002",
      "conflict_type": "Vehicle",
      "replacement": "MH-TRK-003",
      "replacement_name": "Cargo Truck Charlie",
      "resolved": true
    }
  ]
}
```

---

## Database Tables

| Table | Description |
|---|---|
| `plans` | Operation plans with default start time |
| `trips` | Individual vehicle movements with start_offset and duration |
| `routes` | Location pairs with distances (both directions) |
| `locations` | Named locations with coordinates |
| `vehicles` | Vehicles with type, fuel level, and current location |
| `vehicle_types` | Vehicle categories with default speed and capacity |
| `vehicle_availability` | Time windows when vehicles are unavailable |
| `individuals` | Crew members with type and current location |
| `crew_types` | Crew roles (Driver, Commander, Medic, etc.) |
| `individual_availability` | Time windows when crew members are unavailable |
| `trip_crew` | Many-to-many: which crew members are on each trip |
| `load_types` | Cargo types with dimensions and weight |
| `units` | Military units assigned to trips |

---

## Setup

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install flask flask-cors psycopg2-binary
python app.py
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

**Database**

Create a PostgreSQL database named `military_planner` and run the SQL in `db/test.sql` to create and populate all tables.

Update `backend/db.py` with your PostgreSQL credentials.
