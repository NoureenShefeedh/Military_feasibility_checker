-- =========================================================
-- FULL RESET + REBUILD — data.sql
-- =========================================================

TRUNCATE TABLE
    trip_crew,
    individual_availability,
    vehicle_availability,
    trips,
    plans,
    individuals,
    vehicles,
    routes,
    load_types,
    units,
    vehicle_types,
    locations,
    crew_types
RESTART IDENTITY CASCADE;

-- =========================================================
-- CORE REFERENCE DATA
-- =========================================================
INSERT INTO crew_types (crew_type_name) VALUES
('Driver'), ('Helper'), ('Supervisor');

INSERT INTO locations (location_name, latitude, longitude) VALUES
('Location A', 25.276987, 55.296249),
('Location B', 25.204849, 55.270783),
('Location C', 25.197525, 55.274487);

UPDATE locations SET has_fuel_station = TRUE WHERE location_id = 2;
UPDATE locations SET has_fuel_station = TRUE WHERE location_id = 3;

INSERT INTO vehicle_types (type_name, default_speed, max_load_capacity, fuel_capacity, fuel_consumption_rate) VALUES
('Truck Small', 60, 5000, 100, 0.8),
('Truck Medium', 80, 10000, 150, 1.2),
('Truck Large', 100, 20000, 250, 1.8);

INSERT INTO units (unit_name, unit_type, location_id)
VALUES ('Main Depot', 'Hub', 1);

INSERT INTO load_types (load_type_name, height, width, length, weight, volume) VALUES
('Electronics', 1.2, 1.0, 1.5, 100, 2.0),
('Furniture', 2.0, 2.0, 3.0, 200, 10.0),
('Food Supplies', 1.0, 1.0, 1.0, 250, 1.0);

INSERT INTO routes (start_location_id, end_location_id, distance) VALUES
(1, 2, 10.5), (2, 1, 10.5),
(2, 3, 8.2),  (3, 2, 8.2),
(1, 3, 15.0), (3, 1, 15.0);

-- =========================================================
-- VEHICLES
-- =========================================================
INSERT INTO vehicles (vehicle_number, vehicle_name, vehicle_type_id, current_fuel_level, current_location_id, unit_id) VALUES
('V-100', 'Alpha', 1, 100.00, 1, 1),
('V-101', 'Beta', 2, 150.00, 2, 1),
('V-102', 'Gamma', 3, 250.00, 3, 1),
('V-103', 'Delta', 1, 100.00, 1, 1),
('V-104', 'Epsilon', 2, 150.00, 2, 1),
('V-105', 'Omega', 2, 150.00, 3, 1),
('V-200', 'Test8-FuelEmpty', 1, 5.00, 1, 1),
('V-201', 'Test9-FuelDetour', 3, 20.00, 1, 1),
('V-202', 'Test10-WrongLoc', 1, 100.00, 3, 1),
('V-203', 'Test20-FuelExact', 1, 8.40, 1, 1),
('V-204', 'Test21-FuelBelow', 1, 8.30, 1, 1),
('V-205', 'Test19-ZeroFuel', 2, 0.00, 2, 1);

-- =========================================================
-- INDIVIDUALS
-- =========================================================
INSERT INTO individuals (name, crew_type_id, current_location_id) VALUES
('John', 1, 1),
('Mike', 1, 2),
('Ali', 1, 3),
('Sara', 2, 1),
('Ayesha', 2, 2),
('Omar', 3, 3),
('Ravi', 1, 1);

-- =========================================================
-- PLANS
-- =========================================================
INSERT INTO plans (plan_name, num_of_vehicles, default_start_time, total_fuel) VALUES
('Morning Delivery Plan', 3, '08:00:00'::time, 0),
('Dependency Test Plan', 5, '08:00:00'::time, 0),
('Fuel Conflict Tests Plan', 5, '08:00:00'::time, 0),
('Reachability Tests Plan', 2, '08:00:00'::time, 0);

-- =========================================================
-- TRIPS — Morning Delivery Plan
-- =========================================================
INSERT INTO trips (plan_id, vehicle_number, route_id, load_type_id, start_offset, duration, quantity_of_load, unit_id)
SELECT plan_id, 'V-100', 1, 1, '00:00:00'::time, '01:30:00'::time, 10, 1 FROM plans WHERE plan_name = 'Morning Delivery Plan'
UNION ALL
SELECT plan_id, 'V-101', 3, 2, '00:05:00'::time, '02:00:00'::time, 5, 1 FROM plans WHERE plan_name = 'Morning Delivery Plan'
UNION ALL
SELECT plan_id, 'V-102', 5, 3, '00:05:00'::time, '02:30:00'::time, 60, 1 FROM plans WHERE plan_name = 'Morning Delivery Plan';

INSERT INTO trip_crew (trip_id, individual_id)
SELECT t.trip_id, i.individual_id
FROM trips t, individuals i
WHERE t.plan_id = (SELECT plan_id FROM plans WHERE plan_name = 'Morning Delivery Plan')
AND (
    (t.vehicle_number = 'V-100' AND i.name IN ('John','Sara')) OR
    (t.vehicle_number = 'V-101' AND i.name IN ('Mike','Ayesha')) OR
    (t.vehicle_number = 'V-102' AND i.name IN ('Ali','Omar'))
);

-- =========================================================
-- TRIPS — Dependency Test Plan
-- =========================================================
INSERT INTO trips (plan_id, vehicle_number, route_id, load_type_id, start_offset, duration, quantity_of_load, unit_id)
SELECT plan_id, 'V-101', 1, 1, '00:00:00'::time, '01:00:00'::time, 5, 1 FROM plans WHERE plan_name = 'Dependency Test Plan'
UNION ALL
SELECT plan_id, 'V-101', 3, 2, '01:30:00'::time, '01:30:00'::time, 3, 1 FROM plans WHERE plan_name = 'Dependency Test Plan'
UNION ALL
SELECT plan_id, 'V-101', 5, 3, '03:30:00'::time, '02:00:00'::time, 2, 1 FROM plans WHERE plan_name = 'Dependency Test Plan'
UNION ALL
SELECT plan_id, 'V-100', 1, 1, '00:00:00'::time, '01:00:00'::time, 5, 1 FROM plans WHERE plan_name = 'Dependency Test Plan'
UNION ALL
SELECT plan_id, 'V-103', 2, 2, '02:00:00'::time, '01:30:00'::time, 3, 1 FROM plans WHERE plan_name = 'Dependency Test Plan';

-- trip (V-101, route 1) -> John
INSERT INTO trip_crew (trip_id, individual_id)
SELECT t.trip_id, (SELECT individual_id FROM individuals WHERE name = 'John')
FROM trips t WHERE t.plan_id = (SELECT plan_id FROM plans WHERE plan_name = 'Dependency Test Plan')
AND t.vehicle_number = 'V-101' AND t.route_id = 1;

-- trip (V-101, route 3) -> Mike
INSERT INTO trip_crew (trip_id, individual_id)
SELECT t.trip_id, (SELECT individual_id FROM individuals WHERE name = 'Mike')
FROM trips t WHERE t.plan_id = (SELECT plan_id FROM plans WHERE plan_name = 'Dependency Test Plan')
AND t.vehicle_number = 'V-101' AND t.route_id = 3;

-- trip (V-101, route 5) -> Ali
INSERT INTO trip_crew (trip_id, individual_id)
SELECT t.trip_id, (SELECT individual_id FROM individuals WHERE name = 'Ali')
FROM trips t WHERE t.plan_id = (SELECT plan_id FROM plans WHERE plan_name = 'Dependency Test Plan')
AND t.vehicle_number = 'V-101' AND t.route_id = 5;

-- trip (V-100) -> Sara
INSERT INTO trip_crew (trip_id, individual_id)
SELECT t.trip_id, (SELECT individual_id FROM individuals WHERE name = 'Sara')
FROM trips t WHERE t.plan_id = (SELECT plan_id FROM plans WHERE plan_name = 'Dependency Test Plan')
AND t.vehicle_number = 'V-100';

-- trip (V-103) -> Sara
INSERT INTO trip_crew (trip_id, individual_id)
SELECT t.trip_id, (SELECT individual_id FROM individuals WHERE name = 'Sara')
FROM trips t WHERE t.plan_id = (SELECT plan_id FROM plans WHERE plan_name = 'Dependency Test Plan')
AND t.vehicle_number = 'V-103';

-- =========================================================
-- TRIPS — Fuel Conflict Tests Plan
-- =========================================================
INSERT INTO trips (plan_id, vehicle_number, route_id, load_type_id, start_offset, duration, quantity_of_load, unit_id)
SELECT plan_id, 'V-200', 3, 1, '00:00:00'::time, '01:30:00'::time, 5, 1 FROM plans WHERE plan_name = 'Fuel Conflict Tests Plan'
UNION ALL
SELECT plan_id, 'V-201', 5, 3, '00:05:00'::time, '02:30:00'::time, 2, 1 FROM plans WHERE plan_name = 'Fuel Conflict Tests Plan'
UNION ALL
SELECT plan_id, 'V-205', 3, 2, '00:05:00'::time, '01:00:00'::time, 3, 1 FROM plans WHERE plan_name = 'Fuel Conflict Tests Plan'
UNION ALL
SELECT plan_id, 'V-203', 1, 1, '00:00:00'::time, '01:30:00'::time, 5, 1 FROM plans WHERE plan_name = 'Fuel Conflict Tests Plan'
UNION ALL
SELECT plan_id, 'V-204', 1, 1, '00:00:00'::time, '01:30:00'::time, 5, 1 FROM plans WHERE plan_name = 'Fuel Conflict Tests Plan';

-- =========================================================
-- TRIPS — Reachability Tests Plan
-- =========================================================
INSERT INTO trips (plan_id, vehicle_number, route_id, load_type_id, start_offset, duration, quantity_of_load, unit_id)
SELECT plan_id, 'V-202', 1, 1, '00:00:00'::time, '01:30:00'::time, 5, 1 FROM plans WHERE plan_name = 'Reachability Tests Plan'
UNION ALL
SELECT plan_id, 'V-103', 5, 3, '00:05:00'::time, '02:30:00'::time, 2, 1 FROM plans WHERE plan_name = 'Reachability Tests Plan';

INSERT INTO trip_crew (trip_id, individual_id)
SELECT t.trip_id, (SELECT individual_id FROM individuals WHERE name = 'Ali')
FROM trips t
WHERE t.plan_id = (SELECT plan_id FROM plans WHERE plan_name = 'Reachability Tests Plan')
AND t.vehicle_number = 'V-103';

-- =========================================================
-- VEHICLE AVAILABILITY
-- =========================================================
INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-100', 'Maintenance', '2026-07-25 08:00:00'::timestamp, '2026-07-25 12:00:00'::timestamp),
('V-102', 'Engine Failure', '2026-07-27 07:00:00'::timestamp, '2026-07-27 18:00:00'::timestamp),
('V-101', 'Maintenance', '2026-07-30 08:00:00'::timestamp, '2026-07-30 17:00:00'::timestamp),
('V-102', 'Scheduled Inspection', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-104', 'Driver Shortage', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-105', 'Driver Shortage', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-202', 'Blocked during travel window', '2026-08-06 07:45:00'::timestamp, '2026-08-06 08:00:00'::timestamp);

INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-200', 'Reserved', '2026-07-24 00:00:00'::timestamp, '2026-07-24 23:59:00'::timestamp),
('V-200', 'Reserved', '2026-07-25 00:00:00'::timestamp, '2026-07-25 23:59:00'::timestamp),
('V-200', 'Reserved', '2026-07-26 00:00:00'::timestamp, '2026-07-26 23:59:00'::timestamp),
('V-200', 'Reserved', '2026-07-27 00:00:00'::timestamp, '2026-07-27 23:59:00'::timestamp),
('V-200', 'Reserved', '2026-07-30 00:00:00'::timestamp, '2026-07-30 23:59:00'::timestamp),
('V-200', 'Reserved', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-200', 'Reserved', '2026-08-03 00:00:00'::timestamp, '2026-08-03 23:59:00'::timestamp),

('V-201', 'Reserved', '2026-07-24 00:00:00'::timestamp, '2026-07-24 23:59:00'::timestamp),
('V-201', 'Reserved', '2026-07-25 00:00:00'::timestamp, '2026-07-25 23:59:00'::timestamp),
('V-201', 'Reserved', '2026-07-26 00:00:00'::timestamp, '2026-07-26 23:59:00'::timestamp),
('V-201', 'Reserved', '2026-07-27 00:00:00'::timestamp, '2026-07-27 23:59:00'::timestamp),
('V-201', 'Reserved', '2026-07-30 00:00:00'::timestamp, '2026-07-30 23:59:00'::timestamp),
('V-201', 'Reserved', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-201', 'Reserved', '2026-08-03 00:00:00'::timestamp, '2026-08-03 23:59:00'::timestamp),

('V-202', 'Reserved', '2026-07-24 00:00:00'::timestamp, '2026-07-24 23:59:00'::timestamp),
('V-202', 'Reserved', '2026-07-25 00:00:00'::timestamp, '2026-07-25 23:59:00'::timestamp),
('V-202', 'Reserved', '2026-07-26 00:00:00'::timestamp, '2026-07-26 23:59:00'::timestamp),
('V-202', 'Reserved', '2026-07-27 00:00:00'::timestamp, '2026-07-27 23:59:00'::timestamp),
('V-202', 'Reserved', '2026-07-30 00:00:00'::timestamp, '2026-07-30 23:59:00'::timestamp),
('V-202', 'Reserved', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-202', 'Reserved', '2026-08-03 00:00:00'::timestamp, '2026-08-03 23:59:00'::timestamp),
('V-202', 'Reserved', '2026-08-05 00:00:00'::timestamp, '2026-08-05 23:59:00'::timestamp),

('V-203', 'Reserved', '2026-07-24 00:00:00'::timestamp, '2026-07-24 23:59:00'::timestamp),
('V-203', 'Reserved', '2026-07-25 00:00:00'::timestamp, '2026-07-25 23:59:00'::timestamp),
('V-203', 'Reserved', '2026-07-26 00:00:00'::timestamp, '2026-07-26 23:59:00'::timestamp),
('V-203', 'Reserved', '2026-07-27 00:00:00'::timestamp, '2026-07-27 23:59:00'::timestamp),
('V-203', 'Reserved', '2026-07-30 00:00:00'::timestamp, '2026-07-30 23:59:00'::timestamp),
('V-203', 'Reserved', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-203', 'Reserved', '2026-08-03 00:00:00'::timestamp, '2026-08-03 23:59:00'::timestamp),

('V-204', 'Reserved', '2026-07-24 00:00:00'::timestamp, '2026-07-24 23:59:00'::timestamp),
('V-204', 'Reserved', '2026-07-25 00:00:00'::timestamp, '2026-07-25 23:59:00'::timestamp),
('V-204', 'Reserved', '2026-07-26 00:00:00'::timestamp, '2026-07-26 23:59:00'::timestamp),
('V-204', 'Reserved', '2026-07-27 00:00:00'::timestamp, '2026-07-27 23:59:00'::timestamp),
('V-204', 'Reserved', '2026-07-30 00:00:00'::timestamp, '2026-07-30 23:59:00'::timestamp),
('V-204', 'Reserved', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-204', 'Reserved', '2026-08-03 00:00:00'::timestamp, '2026-08-03 23:59:00'::timestamp);

-- =========================================================
-- INDIVIDUAL AVAILABILITY
-- =========================================================
INSERT INTO individual_availability (individual_id, reason, not_available_from, not_available_to)
SELECT individual_id, 'Medical leave', '2026-07-27 07:00:00'::timestamp, '2026-07-27 18:00:00'::timestamp
FROM individuals WHERE name = 'Ravi'
UNION ALL
SELECT individual_id, 'Blocked during travel window', '2026-08-06 07:37:00'::timestamp, '2026-08-06 08:00:00'::timestamp
FROM individuals WHERE name = 'Ali';
INSERT INTO individual_availability (individual_id, reason, not_available_from, not_available_to)
SELECT individual_id, 'Personal leave', '2026-07-30 08:00:00'::timestamp, '2026-07-30 11:30:00'::timestamp
FROM individuals WHERE name = 'Sara';

INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-102', 'Scheduled Inspection', '2026-08-03 00:00:00'::timestamp, '2026-08-03 23:59:00'::timestamp);

INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-205', 'Reserved', '2026-08-02 00:00:00'::timestamp, '2026-08-02 23:59:00'::timestamp),
('V-205', 'Reserved', '2026-08-03 00:00:00'::timestamp, '2026-08-03 23:59:00'::timestamp);

-- New plan
INSERT INTO plans (plan_name, num_of_vehicles, default_start_time, total_fuel)
VALUES ('Combo Round Trip Test Plan', 1, '08:00:00'::time, 0);

-- Trip: V-102, A→C (route 5), Food Supplies, 80 units
INSERT INTO trips (plan_id, vehicle_number, route_id, load_type_id, start_offset, duration, quantity_of_load, unit_id)
SELECT plan_id, 'V-102', 5, 3, '00:00:00'::time, '02:30:00'::time, 80, 1
FROM plans WHERE plan_name = 'Combo Round Trip Test Plan';

-- Block V-102 on 10-Jul (conflict)
INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to)
VALUES ('V-102', 'Maintenance', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp);

-- Block everything except V-100 and V-103 on 10-Jul
INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-101', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp),
('V-104', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp),
('V-105', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp),
('V-200', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp),
('V-201', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp),
('V-202', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp),
('V-203', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp),
('V-204', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp),
('V-205', 'Reserved', '2026-08-10 00:00:00'::timestamp, '2026-08-10 23:59:00'::timestamp);



INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to)
VALUES (
    'V-100',
    'Assigned to Fuel Conflict Tests Plan',
    '2026-08-15 08:00:00'::timestamp,
    '2026-08-15 12:00:00'::timestamp
);

-- John blocked by a low-priority plan assignment on 2026-07-15
INSERT INTO individual_availability (individual_id, reason, not_available_from, not_available_to)
SELECT individual_id,
       'Assigned to Fuel Conflict Tests Plan',
       '2026-08-15 08:00:00'::timestamp,
       '2026-08-15 12:00:00'::timestamp
FROM individuals WHERE name = 'John';

UPDATE plans SET priority = 'low' WHERE plan_name = 'Fuel Conflict Tests Plan';