INSERT INTO crew_types (crew_type_name) VALUES
('Driver'),
('Helper'),
('Supervisor');

INSERT INTO locations (location_name, latitude, longitude) VALUES
('Location A', 25.276987, 55.296249),
('Location B', 25.204849, 55.270783),
('Location C', 25.197525, 55.274487);

INSERT INTO vehicle_types (type_name, default_speed, max_load_capacity, fuel_capacity, fuel_consumption_rate) VALUES
('Truck Small', 60, 5000, 100, 0.8),
('Truck Medium', 80, 10000, 150, 1.2),
('Truck Large', 100, 20000, 250, 1.8);

INSERT INTO units (unit_name, unit_type, location_id)
VALUES ('Main Depot', 'Hub', 1);

INSERT INTO vehicles (vehicle_number, vehicle_name, vehicle_type_id, current_fuel_level, current_location_id, unit_id) VALUES
('V-100', 'Alpha', 1, 80, 1, 1),
('V-101', 'Beta', 2, 120, 2, 1),
('V-102', 'Gamma', 3, 200, 3, 1),
('V-103', 'Delta', 1, 90, 1, 1);

INSERT INTO load_types (load_type_name, height, width, length, weight, volume) VALUES

('Electronics', 1.2, 1.0, 1.5, 100, 2.0), 

('Furniture', 2.0, 2.0, 3.0, 200, 10.0), 

('Food Supplies', 1.0, 1.0, 1.0, 250, 1.0); 

INSERT INTO individuals (name, crew_type_id, current_location_id) VALUES
('John', 1, 1),
('Mike', 1, 2),
('Ali', 1, 3),
('Sara', 2, 1),
('Ayesha', 2, 2),
('Omar', 3, 3);

INSERT INTO routes (start_location_id, end_location_id, distance) VALUES
(1, 2, 10.5),
(2, 1, 10.5),
(2, 3, 8.2),
(3, 2, 8.2),
(1, 3, 15.0),
(3, 1, 15.0);

INSERT INTO plans (plan_name, num_of_vehicles, default_start_time, total_fuel)
VALUES ('Morning Delivery Plan', 3, '08:00:00', 0);

INSERT INTO trips (
    plan_id,
    vehicle_number,
    route_id,
    load_type_id,
    start_offset,
    duration,
    quantity_of_load,
    unit_id
) VALUES
-- Trip 1
(1, 'V-100', 1, 1, '00:00:00', '01:30:00', 100, 1),

-- Trip 2
(1, 'V-101', 3, 2, '00:05:00', '02:00:00', 200, 1),

-- Trip 3
(1, 'V-102', 5, 3, '00:05:00', '02:30:00', 150, 1);

INSERT INTO trip_crew (trip_id, individual_id) VALUES
(1, 1),
(1, 4),

(2, 2),
(2, 5),

(3, 3),
(3, 6);

INSERT INTO vehicle_availability (
    vehicle_number,
    reason,
    not_available_from,
    not_available_to
)
VALUES (
    'V-100',
    'Maintenance',
    '2026-06-25 08:00:00',
    '2026-06-25 12:00:00'
);
UPDATE vehicles v
SET current_fuel_level = vt.fuel_capacity
FROM vehicle_types vt
WHERE v.vehicle_type_id = vt.vehicle_type_id;

UPDATE trips
SET quantity_of_load = 10
WHERE trip_id = 1;

UPDATE trips
SET quantity_of_load = 5
WHERE trip_id = 2;

UPDATE trips
SET quantity_of_load = 60
WHERE trip_id = 3;

INSERT INTO vehicle_availability (
    vehicle_number,
    reason,
    not_available_from,
    not_available_to
)
VALUES (
    'V-102',
    'Engine Failure',
    '2026-06-27 07:00:00',
    '2026-06-27 18:00:00'
);

INSERT INTO vehicles (
    vehicle_number,
    vehicle_name,
    vehicle_type_id,
    current_fuel_level,
    current_location_id,
    unit_id
)
VALUES (
    'V-104',
    'Epsilon',
    2,
    150.00,
    2,
    1
);
INSERT INTO vehicles (
    vehicle_number,
    vehicle_name,
    vehicle_type_id,
    current_fuel_level,
    current_location_id,
    unit_id
)
VALUES (
    'V-105',
    'Omega',
    2,
    150.00,
    3,
    1
);
INSERT INTO individuals (name, crew_type_id, current_location_id)
VALUES
('Ravi', 1, 1);

INSERT INTO individual_availability (
    individual_id,
    reason,
    not_available_from,
    not_available_to
)
VALUES (
    1,
    'Medical leave',
    '2026-06-27 07:00:00',
    '2026-06-27 18:00:00'
);

INSERT INTO plans (plan_name, num_of_vehicles, default_start_time, total_fuel)
VALUES ('Dependency Test Plan', 5, '08:00:00', 0);

INSERT INTO trips (
    plan_id, vehicle_number, route_id, load_type_id,
    start_offset, duration, quantity_of_load, unit_id
) VALUES

-- Trip 1
(2, 'V-101', 1, 1, '00:00:00', '01:00:00', 5, 1),

-- Trip 2
(2, 'V-101', 3, 2, '00:00:00', '01:30:00', 3, 1),

-- Trip 3
(2, 'V-101', 5, 3, '00:00:00', '02:00:00', 2, 1);

INSERT INTO trips (
    plan_id, vehicle_number, route_id, load_type_id,
    start_offset, duration, quantity_of_load, unit_id
) VALUES

-- Trip 4
(2, 'V-100', 1, 1, '00:00:00', '01:00:00', 5, 1),

-- Trip 5
(2, 'V-103', 2, 2, '02:00:00', '01:30:00', 3, 1);


INSERT INTO trip_crew (trip_id, individual_id) VALUES 
(4, 1),
(5, 2),
(6, 3),
(7,4),
(8,4);

INSERT INTO vehicle_availability (
    vehicle_number,
    not_available_from,
    not_available_to,
    reason
)
VALUES (
    'V-101',
    '2026-06-30 08:00:00',
    '2026-06-30 17:00:00',
    'Maintenance'
);

INSERT INTO vehicle_availability (
    vehicle_number,
    reason,
    not_available_from,
    not_available_to
)
VALUES (
    'V-102',
    'Scheduled Inspection',
    '2026-07-02 00:00:00',
    '2026-07-02 23:59:00'
);
-- Make V-104 unavailable on July 2nd
INSERT INTO vehicle_availability (
    vehicle_number,
    reason,
    not_available_from,
    not_available_to
)
VALUES (
    'V-104',
    'Driver Shortage',
    '2026-07-02 00:00:00',
    '2026-07-02 23:59:00'
);

-- Make V-105 unavailable on July 2nd
INSERT INTO vehicle_availability (
    vehicle_number,
    reason,
    not_available_from,
    not_available_to
)
VALUES (
    'V-105',
    'Driver Shortage',
    '2026-07-02 00:00:00',
    '2026-07-02 23:59:00'
);
UPDATE locations
SET has_fuel_station = TRUE
WHERE location_id = 2;
UPDATE locations
SET has_fuel_station = TRUE
WHERE location_id = 3;

INSERT INTO vehicles (vehicle_number, vehicle_name, vehicle_type_id, current_fuel_level, current_location_id, unit_id)
VALUES ('V-200', 'Test8-FuelEmpty', 1, 5.0, 1, 1);

INSERT INTO vehicles (vehicle_number, vehicle_name, vehicle_type_id, current_fuel_level, current_location_id, unit_id)
VALUES ('V-201', 'Test9-FuelDetour', 3, 20.0, 1, 1);

INSERT INTO vehicles (vehicle_number, vehicle_name, vehicle_type_id, current_fuel_level, current_location_id, unit_id)
VALUES ('V-202', 'Test10-WrongLoc', 1, 100.0, 3, 1);

INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to)
VALUES ('V-202', 'Blocked during travel window', '2026-07-06 07:45:00', '2026-07-06 08:00:00');

INSERT INTO vehicles (vehicle_number, vehicle_name, vehicle_type_id, current_fuel_level, current_location_id, unit_id)
VALUES ('V-205', 'Test19-ZeroFuel', 2, 0.0, 2, 1);

INSERT INTO vehicles (vehicle_number, vehicle_name, vehicle_type_id, current_fuel_level, current_location_id, unit_id)
VALUES ('V-203', 'Test20-FuelExact', 1, 8.4, 1, 1);

INSERT INTO vehicles (vehicle_number, vehicle_name, vehicle_type_id, current_fuel_level, current_location_id, unit_id)
VALUES ('V-204', 'Test21-FuelBelow', 1, 8.3, 1, 1);


INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-200', 'Reserved', '2026-06-24 00:00:00', '2026-06-24 23:59:00'),
('V-200', 'Reserved', '2026-06-25 00:00:00', '2026-06-25 23:59:00'),
('V-200', 'Reserved', '2026-06-26 00:00:00', '2026-06-26 23:59:00'),
('V-200', 'Reserved', '2026-06-27 00:00:00', '2026-06-27 23:59:00'),
('V-200', 'Reserved', '2026-06-30 00:00:00', '2026-06-30 23:59:00'),
('V-200', 'Reserved', '2026-07-02 00:00:00', '2026-07-02 23:59:00'),
('V-200', 'Reserved', '2026-07-03 00:00:00', '2026-07-03 23:59:00');

INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-201', 'Reserved', '2026-06-24 00:00:00', '2026-06-24 23:59:00'),
('V-201', 'Reserved', '2026-06-25 00:00:00', '2026-06-25 23:59:00'),
('V-201', 'Reserved', '2026-06-26 00:00:00', '2026-06-26 23:59:00'),
('V-201', 'Reserved', '2026-06-27 00:00:00', '2026-06-27 23:59:00'),
('V-201', 'Reserved', '2026-06-30 00:00:00', '2026-06-30 23:59:00'),
('V-201', 'Reserved', '2026-07-02 00:00:00', '2026-07-02 23:59:00'),
('V-201', 'Reserved', '2026-07-03 00:00:00', '2026-07-03 23:59:00');

INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-202', 'Reserved', '2026-06-24 00:00:00', '2026-06-24 23:59:00'),
('V-202', 'Reserved', '2026-06-25 00:00:00', '2026-06-25 23:59:00'),
('V-202', 'Reserved', '2026-06-26 00:00:00', '2026-06-26 23:59:00'),
('V-202', 'Reserved', '2026-06-27 00:00:00', '2026-06-27 23:59:00'),
('V-202', 'Reserved', '2026-06-30 00:00:00', '2026-06-30 23:59:00'),
('V-202', 'Reserved', '2026-07-02 00:00:00', '2026-07-02 23:59:00'),
('V-202', 'Reserved', '2026-07-03 00:00:00', '2026-07-03 23:59:00');

INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-203', 'Reserved', '2026-06-24 00:00:00', '2026-06-24 23:59:00'),
('V-203', 'Reserved', '2026-06-25 00:00:00', '2026-06-25 23:59:00'),
('V-203', 'Reserved', '2026-06-26 00:00:00', '2026-06-26 23:59:00'),
('V-203', 'Reserved', '2026-06-27 00:00:00', '2026-06-27 23:59:00'),
('V-203', 'Reserved', '2026-06-30 00:00:00', '2026-06-30 23:59:00'),
('V-203', 'Reserved', '2026-07-02 00:00:00', '2026-07-02 23:59:00'),
('V-203', 'Reserved', '2026-07-03 00:00:00', '2026-07-03 23:59:00');


INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-204', 'Reserved', '2026-06-24 00:00:00', '2026-06-24 23:59:00'),
('V-204', 'Reserved', '2026-06-25 00:00:00', '2026-06-25 23:59:00'),
('V-204', 'Reserved', '2026-06-26 00:00:00', '2026-06-26 23:59:00'),
('V-204', 'Reserved', '2026-06-27 00:00:00', '2026-06-27 23:59:00'),
('V-204', 'Reserved', '2026-06-30 00:00:00', '2026-06-30 23:59:00'),
('V-204', 'Reserved', '2026-07-02 00:00:00', '2026-07-02 23:59:00'),
('V-204', 'Reserved', '2026-07-03 00:00:00', '2026-07-03 23:59:00');


INSERT INTO vehicle_availability (vehicle_number, reason, not_available_from, not_available_to) VALUES
('V-205', 'Reserved', '2026-06-24 00:00:00', '2026-06-24 23:59:00'),
('V-205', 'Reserved', '2026-06-25 00:00:00', '2026-06-25 23:59:00'),
('V-205', 'Reserved', '2026-06-26 00:00:00', '2026-06-26 23:59:00'),
('V-205', 'Reserved', '2026-06-27 00:00:00', '2026-06-27 23:59:00'),
('V-205', 'Reserved', '2026-06-30 00:00:00', '2026-06-30 23:59:00'),
('V-205', 'Reserved', '2026-07-02 00:00:00', '2026-07-02 23:59:00'),
('V-205', 'Reserved', '2026-07-03 00:00:00', '2026-07-03 23:59:00');


INSERT INTO plans (plan_name, num_of_vehicles, default_start_time, total_fuel)
VALUES ('Fuel Conflict Tests Plan', 5, '08:00:00', 0);

INSERT INTO trips (plan_id, vehicle_number, route_id, load_type_id, start_offset, duration, quantity_of_load, unit_id) VALUES
-- Test 8:  V-200, A→B (route 1), fuel=5L → conflict
(3, 'V-200', 1, 1, '00:00:00', '01:30:00', 5, 1),
-- Test 9:  V-201, A→C (route 5), fuel=20L → detour via B → no conflict
(3, 'V-201', 5, 3, '00:05:00', '02:30:00', 2, 1),
-- Test 19: V-205, B→C (route 3), fuel=0L, at B which has station → no conflict
(3, 'V-205', 3, 2, '00:05:00', '01:00:00', 3, 1),
-- Test 20: V-203, A→B (route 1), fuel=8.4L → exactly at threshold → no conflict
(3, 'V-203', 1, 1, '00:00:00', '01:30:00', 5, 1),
-- Test 21: V-204, A→B (route 1), fuel=8.3L → just below → conflict
(3, 'V-204', 1, 1, '00:00:00', '01:30:00', 5, 1);

INSERT INTO plans (plan_name, num_of_vehicles, default_start_time, total_fuel)
VALUES ('Reachability Tests Plan', 2, '08:00:00', 0);

INSERT INTO trips (plan_id, vehicle_number, route_id, load_type_id, start_offset, duration, quantity_of_load, unit_id)
VALUES (4, 'V-202', 1, 1, '00:00:00', '01:30:00', 5, 1);
INSERT INTO trips (plan_id, vehicle_number, route_id, load_type_id, start_offset, duration, quantity_of_load, unit_id)
VALUES (4, 'V-103', 5, 3, '00:05:00', '02:30:00', 2, 1);

INSERT INTO trip_crew (trip_id, individual_id)
VALUES (
    (SELECT trip_id FROM trips WHERE plan_id = 4 AND vehicle_number = 'V-103'),
    3   -- Ali, current_location_id=3 (Loc C)
);

INSERT INTO individual_availability (individual_id, reason, not_available_from, not_available_to)
VALUES (3, 'Blocked during travel window', '2026-07-06 07:37:00', '2026-07-06 08:00:00');

UPDATE vehicles SET current_location_id = 3 WHERE vehicle_number = 'V-200';