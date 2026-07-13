# Military Plan Feasibility System

A web application for checking whether military operation plans can be executed on a given date and time while considering vehicle availability, personnel availability, travel times, fuel constraints, and shared resource limitations.

The system evaluates assigned resources for each trip, detects conflicts, suggests replacements when possible, and determines the next feasible execution time when the operation cannot be performed at the requested time.

---

# Tech Stack

| Layer    | Technology     |
| -------- | -------------- |
| Frontend | React          |
| Backend  | Flask (Python) |
| Database | PostgreSQL     |

---

# Project Structure

```
project/
│
├── backend/
│   ├── app.py                  # Flask application entry point
│   ├── db.py                   # PostgreSQL database connection
│   │
│   └── routes/
│       ├── plans.py             # API routes
│       ├── scheduler.py          # Feasibility checking and scheduling logic
│       └── resolver.py           # Conflict resolution and next feasible time search
│
└── frontend/
    └── src/
        ├── pages/
        │   ├── Plans.jsx         # Operation plans and trip details
        │   └── Feasibility.jsx   # Feasibility checking interface
        │
        ├── components/
        │   ├── TripCard.jsx
        │   ├── ConflictTable.jsx
        │   └── ResolutionTable.jsx
        │
        └── api/
            └── plans.js           # Backend API calls
```

---

# Core Concepts

## Plans and Trips

A **plan** represents a military operation. Each plan contains multiple trips representing individual vehicle movements between locations.

Each plan has a default starting time (**T0**).

A trip is defined using:

* `start_offset` — time after T0 when loading/preparation begins
* `duration` — time required to complete the trip

The trip timeline is calculated as:

```
actual_start = T0 + start_offset

actual_end = actual_start + duration
```

If the user provides a custom date and time, that value is used as the new T0 instead of the default plan start time.

---

# Feasibility Check

A plan is considered feasible when every assigned vehicle and crew member:

* Is available for the complete duration of their assigned trip
* Can physically reach the required starting location before the trip begins
* Has sufficient fuel to complete the required movement
* Does not conflict with another assigned trip using the same resource

The system checks:

* Vehicle availability
* Personnel availability
* Travel time between locations
* Fuel requirements
* Shared resource usage
* Route reachability

---

# Resource Reachability

Resources are required to be present at the trip starting location before loading/preparation begins.

The system calculates whether a resource can travel from its current location to the trip start location in time.

The resource must:

* Be free during the travel period
* Complete travel before the trip begins
* Have enough fuel for required movement

If a resource cannot reach the required location in time, a reachability conflict is generated.

---

# Shared Resources

A vehicle or crew member may be assigned to multiple trips within the same plan.

The system keeps the original trip order defined in the plan.

For shared resources:

* Trips cannot overlap
* A resource must finish its previous trip before starting another
* Travel time between consecutive trips is considered
* The resource must be able to reach the next trip's starting location before it begins

If a shared resource cannot complete all assigned trips due to availability, travel, or fuel limitations, the system reports the conflict.

The system does **not reorder trips**. The original operation sequence is always maintained.

---

# Conflict Detection

When a plan cannot be executed, the system identifies the exact cause of failure.

Supported conflict types include:

## Vehicle Conflicts

Examples:

* Vehicle unavailable during required time
* Vehicle cannot reach the trip location
* Insufficient fuel
* No suitable replacement vehicle available

## Personnel Conflicts

Examples:

* Crew member unavailable
* Crew member cannot reach required location
* No suitable replacement personnel available

Each conflict includes:

* Trip ID
* Resource identifier
* Conflict type
* Conflict reason
* Availability window
* Required execution window

---

# Conflict Resolution

When a resource conflict occurs, the system attempts to find a replacement.

For a vehicle conflict:

The system searches for another vehicle that:

* Has the same vehicle type
* Is not already assigned to the plan
* Is available during the required period
* Can reach the required starting location before the trip begins
* Has sufficient fuel capacity

For a crew conflict:

The system searches for another individual who:

* Has the same crew type
* Is available during the required period
* Can reach the required location before the trip begins

If no valid replacement exists, the system reports that no suitable replacement is available.

---

# Next Feasible Execution Time

If a plan cannot be executed at the requested date and time using the currently assigned resources, the system searches for the earliest possible execution time.

The resolver calculates a future T0 where the same assigned resources can successfully complete the operation while maintaining the original trip sequence.

The search considers:

* Existing vehicle unavailability periods
* Personnel unavailability periods
* Travel time requirements
* Fuel availability
* Shared resource constraints

If a valid time is found, the system returns:

* The next feasible execution time
* Updated trip schedule
* Resource availability status

---

# Availability Management

The system maintains resource availability dynamically.

Before performing feasibility checks, expired entries from the unavailability tables are removed.

This prevents outdated records from affecting future scheduling decisions.

The cleanup process ensures:

* Completed unavailable periods are removed
* Only active availability restrictions are considered
* Vehicle and personnel availability data remains accurate

The system manages:

* `vehicle_availability`
* `individual_availability`

---

# API Endpoints

| Method | Endpoint                 | Description                                                |
| ------ | ------------------------ | ---------------------------------------------------------- |
| GET    | `/api/plans`             | Retrieve all operation plans                               |
| GET    | `/api/plans/<id>/trips`  | Retrieve trips with vehicle, crew, load, and route details |
| POST   | `/api/plans/feasibility` | Perform feasibility check for a plan                       |

---

# Feasibility Request

Example:

```json
{
  "plan_id": 2,
  "date": "2026-06-11",
  "time": "06:00"
}
```

`time` is optional.

If not provided, the plan's default start time is used.

---

# Feasibility Response

Example:

```json
{
  "feasible": false,
  "schedule": [
    {
      "trip_id": 4,
      "actual_start": "2026-06-11T06:10:00",
      "actual_end": "2026-06-11T11:10:00"
    }
  ],
  "conflicts": [
    {
      "trip_id": 5,
      "identifier": "MH-TRK-002",
      "conflict_type": "Vehicle",
      "conflict_subtype": "unavailable",
      "reason": "Fuel Refill",
      "earliest_available": "2026-06-11T13:00:00"
    }
  ],
  "resolutions": [
    {
      "trip_id": 5,
      "original": "MH-TRK-002",
      "replacement": "MH-TRK-003",
      "resolved": true
    }
  ]
}
```

---

# Database Tables

| Table                   | Description                                            |
| ----------------------- | ------------------------------------------------------ |
| plans                   | Military operation plans with default start times      |
| trips                   | Individual vehicle movements with offsets and duration |
| routes                  | Location-to-location distances                         |
| locations               | Named locations and coordinates                        |
| vehicles                | Vehicle details, fuel level, and current location      |
| vehicle_types           | Vehicle categories, speed, and fuel capacity           |
| vehicle_availability    | Vehicle unavailable time periods                       |
| individuals             | Crew members and their current locations               |
| crew_types              | Crew roles such as Driver, Commander, Medic            |
| individual_availability | Personnel unavailable time periods                     |
| trip_crew               | Mapping between trips and assigned crew members        |
| load_types              | Cargo information                                      |
| units                   | Military units assigned to trips                       |

---

# Setup

## Backend

Navigate to backend:

```bash
cd backend
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install flask flask-cors psycopg2-binary
```

Run backend:

```bash
python app.py
```

---

## Frontend

Navigate to frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start application:

```bash
npm run dev
```

---

## Database Setup

Create PostgreSQL database:

```
military_planner
```

Execute the SQL file:

```
db/schema.sql
db/data.sql
```

to create and populate all required tables.

Update PostgreSQL credentials in:

```
backend/db.py
```

---

# Features Summary

✓ Military operation feasibility checking
✓ Vehicle and personnel availability validation
✓ Travel time and reachability calculation
✓ Fuel constraint checking
✓ Shared resource conflict detection
✓ Replacement resource suggestions
✓ Next feasible execution time calculation
✓ Maintains original trip sequence
✓ Removes expired unavailability records
✓ React-based user interface
✓ Flask REST API backend
✓ PostgreSQL data management
