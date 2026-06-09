--
-- PostgreSQL database dump
--

\restrict AVFuLS9jBZdVTw2gLphJbHwfuHGceW5zHoNYSBU98mMr3XTubLaqRQzQVnj0TMW

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

-- Started on 2026-06-09 12:45:58

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 5122 (class 0 OID 24674)
-- Dependencies: 228
-- Data for Name: crew_types; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.crew_types VALUES (1, 'Driver');
INSERT INTO public.crew_types VALUES (2, 'Commander');
INSERT INTO public.crew_types VALUES (3, 'Co-Driver');
INSERT INTO public.crew_types VALUES (4, 'Navigator');
INSERT INTO public.crew_types VALUES (5, 'Gunner');
INSERT INTO public.crew_types VALUES (6, 'Loader');
INSERT INTO public.crew_types VALUES (7, 'Radio Operator');
INSERT INTO public.crew_types VALUES (8, 'Mechanic');
INSERT INTO public.crew_types VALUES (9, 'Medic');
INSERT INTO public.crew_types VALUES (10, 'Engineer');
INSERT INTO public.crew_types VALUES (11, 'Technician');
INSERT INTO public.crew_types VALUES (12, 'Security Personnel');


--
-- TOC entry 5116 (class 0 OID 24617)
-- Dependencies: 222
-- Data for Name: locations; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.locations VALUES (1, 'Alpha Base', 12.97160000, 77.59460000);
INSERT INTO public.locations VALUES (2, 'Bravo Base', 13.08270000, 80.27070000);
INSERT INTO public.locations VALUES (3, 'Central Logistics Hub', 17.38500000, 78.48670000);
INSERT INTO public.locations VALUES (4, 'Northern Supply Depot', 28.61390000, 77.20900000);
INSERT INTO public.locations VALUES (5, 'Southern Supply Depot', 8.52410000, 76.93660000);
INSERT INTO public.locations VALUES (6, 'Eastern Checkpoint', 22.57260000, 88.36390000);
INSERT INTO public.locations VALUES (7, 'Western Checkpoint', 19.07610000, 72.87740000);
INSERT INTO public.locations VALUES (8, 'Forward Operating Base', 15.29930000, 74.12400000);
INSERT INTO public.locations VALUES (9, 'Air Operations Center', 26.91240000, 75.78730000);
INSERT INTO public.locations VALUES (10, 'Naval Dockyard', 18.93880000, 72.83530000);
INSERT INTO public.locations VALUES (11, 'Mountain Outpost', 30.73330000, 76.77940000);
INSERT INTO public.locations VALUES (12, 'Desert Camp', 26.23890000, 73.02430000);
INSERT INTO public.locations VALUES (13, 'Training Ground', 11.01680000, 76.95580000);
INSERT INTO public.locations VALUES (14, 'Medical Support Center', 23.02250000, 72.57140000);
INSERT INTO public.locations VALUES (15, 'Reserve Storage Facility', 21.14580000, 79.08820000);


--
-- TOC entry 5124 (class 0 OID 24702)
-- Dependencies: 230
-- Data for Name: individuals; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.individuals VALUES (1, 'John Smith', 1, 1);
INSERT INTO public.individuals VALUES (2, 'Michael Brown', 2, 1);
INSERT INTO public.individuals VALUES (3, 'David Wilson', 5, 2);
INSERT INTO public.individuals VALUES (4, 'James Taylor', 4, 2);
INSERT INTO public.individuals VALUES (5, 'Robert Davis', 3, 3);
INSERT INTO public.individuals VALUES (6, 'William Moore', 8, 4);
INSERT INTO public.individuals VALUES (7, 'Joseph Anderson', 7, 5);
INSERT INTO public.individuals VALUES (8, 'Thomas Jackson', 6, 6);
INSERT INTO public.individuals VALUES (9, 'Charles White', 1, 7);
INSERT INTO public.individuals VALUES (10, 'Daniel Harris', 2, 8);
INSERT INTO public.individuals VALUES (12, 'Anthony Garcia', 9, 10);
INSERT INTO public.individuals VALUES (15, 'Steven Robinson', 8, 5);
INSERT INTO public.individuals VALUES (16, 'Paul Clark', 7, 6);
INSERT INTO public.individuals VALUES (17, 'Andrew Lewis', 5, 7);
INSERT INTO public.individuals VALUES (18, 'Kenneth Walker', 6, 8);
INSERT INTO public.individuals VALUES (20, 'Kevin Young', 2, 10);
INSERT INTO public.individuals VALUES (13, 'Mark Thompson', 1, 1);
INSERT INTO public.individuals VALUES (14, 'Donald Martinez', 4, 1);
INSERT INTO public.individuals VALUES (19, 'Joshua Hall', 1, 3);
INSERT INTO public.individuals VALUES (11, 'Matthew Martin', 3, 3);


--
-- TOC entry 5135 (class 0 OID 24916)
-- Dependencies: 241
-- Data for Name: individual_availability; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.individual_availability VALUES (1, 1, 'Assigned to Mission A', '2026-06-10 09:00:00', '2026-06-10 11:30:00');
INSERT INTO public.individual_availability VALUES (2, 2, 'Leave', '2026-06-11 00:00:00', '2026-06-11 23:59:00');
INSERT INTO public.individual_availability VALUES (3, 3, 'Training', '2026-06-12 10:00:00', '2026-06-12 14:00:00');
INSERT INTO public.individual_availability VALUES (4, 4, 'Medical Duty', '2026-06-13 08:00:00', '2026-06-13 12:00:00');
INSERT INTO public.individual_availability VALUES (5, 5, 'Security Assignment', '2026-06-14 09:00:00', '2026-06-14 12:00:00');
INSERT INTO public.individual_availability VALUES (6, 6, 'Vehicle Repair Duty', '2026-06-10 07:00:00', '2026-06-10 10:00:00');
INSERT INTO public.individual_availability VALUES (7, 7, 'Comms Drill', '2026-06-11 13:00:00', '2026-06-11 15:00:00');
INSERT INTO public.individual_availability VALUES (8, 9, 'Medical Checkup', '2026-06-12 08:00:00', '2026-06-12 09:30:00');
INSERT INTO public.individual_availability VALUES (9, 12, 'Field Medic Assignment', '2026-06-13 06:00:00', '2026-06-13 14:00:00');
INSERT INTO public.individual_availability VALUES (10, 17, 'Gunnery Training', '2026-06-14 10:00:00', '2026-06-14 13:00:00');


--
-- TOC entry 5128 (class 0 OID 24746)
-- Dependencies: 234
-- Data for Name: load_types; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.load_types VALUES (1, 'Ammunition Crate', 0.80, 0.60, 1.20, 500.00, 0.58);
INSERT INTO public.load_types VALUES (2, 'Fuel Container', 1.50, 1.20, 1.20, 1000.00, 2.16);
INSERT INTO public.load_types VALUES (3, 'Medical Supplies', 0.50, 0.50, 0.80, 150.00, 0.20);
INSERT INTO public.load_types VALUES (4, 'Food Rations', 1.00, 1.00, 1.50, 750.00, 1.50);
INSERT INTO public.load_types VALUES (5, 'Communication Equipment', 0.70, 0.60, 1.00, 300.00, 0.42);
INSERT INTO public.load_types VALUES (6, 'Spare Parts', 1.20, 1.00, 1.50, 1200.00, 1.80);
INSERT INTO public.load_types VALUES (7, 'Engineering Equipment', 2.00, 1.50, 3.00, 5000.00, 9.00);
INSERT INTO public.load_types VALUES (8, 'Water Tank', 2.20, 2.00, 3.50, 8000.00, 15.40);
INSERT INTO public.load_types VALUES (9, 'Missile Component', 1.00, 1.00, 4.00, 2500.00, 4.00);
INSERT INTO public.load_types VALUES (10, 'Vehicle Engine', 1.50, 1.20, 2.00, 1800.00, 3.60);


--
-- TOC entry 5130 (class 0 OID 24831)
-- Dependencies: 236
-- Data for Name: plans; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.plans VALUES (1, 'Operation Alpha', 3, '06:00:00', 1500.00);
INSERT INTO public.plans VALUES (2, 'Supply Mission Bravo', 4, '05:00:00', 2200.00);
INSERT INTO public.plans VALUES (3, 'Medical Evac Delta', 2, '08:00:00', 800.00);
INSERT INTO public.plans VALUES (4, 'Fuel Resupply Echo', 2, '07:00:00', 1800.00);
INSERT INTO public.plans VALUES (5, 'Northern Push Foxtrot', 3, '04:00:00', 3000.00);
INSERT INTO public.plans VALUES (6, 'Shared Vehicle Feasible Test', 2, '07:00:00', 1200.00);
INSERT INTO public.plans VALUES (7, 'Shared Resource Conflict Test', 2, '08:00:00', 1000.00);


--
-- TOC entry 5126 (class 0 OID 24724)
-- Dependencies: 232
-- Data for Name: routes; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.routes VALUES (1, 1, 3, 510.00);
INSERT INTO public.routes VALUES (2, 3, 4, 1480.00);
INSERT INTO public.routes VALUES (3, 1, 5, 680.00);
INSERT INTO public.routes VALUES (4, 3, 8, 370.00);
INSERT INTO public.routes VALUES (5, 4, 9, 240.00);
INSERT INTO public.routes VALUES (6, 7, 10, 15.00);
INSERT INTO public.routes VALUES (7, 1, 13, 350.00);
INSERT INTO public.routes VALUES (8, 2, 6, 1670.00);
INSERT INTO public.routes VALUES (9, 9, 11, 430.00);
INSERT INTO public.routes VALUES (10, 12, 9, 130.00);
INSERT INTO public.routes VALUES (11, 14, 7, 390.00);
INSERT INTO public.routes VALUES (12, 5, 13, 160.00);
INSERT INTO public.routes VALUES (13, 8, 1, 370.00);
INSERT INTO public.routes VALUES (14, 3, 15, 480.00);
INSERT INTO public.routes VALUES (15, 11, 4, 370.00);
INSERT INTO public.routes VALUES (16, 2, 1, 350.00);
INSERT INTO public.routes VALUES (17, 3, 1, 510.00);
INSERT INTO public.routes VALUES (18, 4, 1, 1750.00);
INSERT INTO public.routes VALUES (19, 5, 1, 680.00);
INSERT INTO public.routes VALUES (20, 6, 1, 1870.00);
INSERT INTO public.routes VALUES (21, 7, 1, 980.00);
INSERT INTO public.routes VALUES (22, 8, 1, 370.00);
INSERT INTO public.routes VALUES (23, 9, 1, 1700.00);
INSERT INTO public.routes VALUES (24, 10, 1, 990.00);
INSERT INTO public.routes VALUES (25, 11, 1, 1950.00);
INSERT INTO public.routes VALUES (26, 12, 1, 1600.00);
INSERT INTO public.routes VALUES (27, 13, 1, 350.00);
INSERT INTO public.routes VALUES (28, 14, 1, 1250.00);
INSERT INTO public.routes VALUES (29, 15, 1, 850.00);
INSERT INTO public.routes VALUES (30, 1, 2, 350.00);
INSERT INTO public.routes VALUES (31, 3, 2, 630.00);
INSERT INTO public.routes VALUES (32, 4, 2, 2200.00);
INSERT INTO public.routes VALUES (33, 5, 2, 760.00);
INSERT INTO public.routes VALUES (34, 6, 2, 1360.00);
INSERT INTO public.routes VALUES (35, 7, 2, 1340.00);
INSERT INTO public.routes VALUES (36, 8, 2, 730.00);
INSERT INTO public.routes VALUES (37, 9, 2, 1900.00);
INSERT INTO public.routes VALUES (38, 10, 2, 1330.00);
INSERT INTO public.routes VALUES (39, 11, 2, 2350.00);
INSERT INTO public.routes VALUES (40, 12, 2, 1800.00);
INSERT INTO public.routes VALUES (41, 4, 3, 1480.00);
INSERT INTO public.routes VALUES (42, 5, 3, 1150.00);
INSERT INTO public.routes VALUES (43, 6, 3, 1500.00);
INSERT INTO public.routes VALUES (44, 7, 3, 710.00);
INSERT INTO public.routes VALUES (45, 8, 3, 370.00);
INSERT INTO public.routes VALUES (46, 9, 3, 1260.00);
INSERT INTO public.routes VALUES (47, 10, 3, 710.00);
INSERT INTO public.routes VALUES (48, 11, 3, 1650.00);
INSERT INTO public.routes VALUES (49, 12, 3, 980.00);
INSERT INTO public.routes VALUES (50, 15, 3, 480.00);
INSERT INTO public.routes VALUES (51, 13, 5, 160.00);
INSERT INTO public.routes VALUES (52, 5, 12, 620.00);
INSERT INTO public.routes VALUES (53, 7, 14, 390.00);
INSERT INTO public.routes VALUES (54, 10, 7, 15.00);
INSERT INTO public.routes VALUES (55, 9, 12, 130.00);
INSERT INTO public.routes VALUES (56, 4, 11, 370.00);
INSERT INTO public.routes VALUES (57, 2, 3, 630.00);
INSERT INTO public.routes VALUES (58, 1, 4, 1739.80);
INSERT INTO public.routes VALUES (59, 1, 6, 1560.70);
INSERT INTO public.routes VALUES (60, 1, 7, 845.35);
INSERT INTO public.routes VALUES (61, 1, 8, 454.99);
INSERT INTO public.routes VALUES (62, 1, 9, 1561.54);
INSERT INTO public.routes VALUES (63, 1, 10, 835.98);
INSERT INTO public.routes VALUES (64, 1, 11, 1976.78);
INSERT INTO public.routes VALUES (65, 1, 12, 1550.53);
INSERT INTO public.routes VALUES (66, 1, 14, 1237.04);
INSERT INTO public.routes VALUES (67, 1, 15, 922.66);
INSERT INTO public.routes VALUES (68, 2, 4, 1755.80);
INSERT INTO public.routes VALUES (69, 2, 5, 624.08);
INSERT INTO public.routes VALUES (70, 2, 7, 1033.13);
INSERT INTO public.routes VALUES (71, 2, 8, 706.92);
INSERT INTO public.routes VALUES (72, 2, 9, 1607.10);
INSERT INTO public.routes VALUES (73, 2, 10, 1027.05);
INSERT INTO public.routes VALUES (74, 2, 11, 1995.05);
INSERT INTO public.routes VALUES (75, 2, 12, 1646.89);
INSERT INTO public.routes VALUES (76, 2, 13, 427.43);
INSERT INTO public.routes VALUES (77, 2, 14, 1371.81);
INSERT INTO public.routes VALUES (78, 2, 15, 905.32);
INSERT INTO public.routes VALUES (79, 3, 5, 999.47);
INSERT INTO public.routes VALUES (80, 3, 6, 1181.88);
INSERT INTO public.routes VALUES (81, 3, 7, 621.50);
INSERT INTO public.routes VALUES (82, 3, 9, 1095.15);
INSERT INTO public.routes VALUES (83, 3, 10, 621.55);
INSERT INTO public.routes VALUES (84, 3, 11, 1494.28);
INSERT INTO public.routes VALUES (85, 3, 12, 1134.14);
INSERT INTO public.routes VALUES (86, 3, 13, 727.06);
INSERT INTO public.routes VALUES (87, 3, 14, 879.50);
INSERT INTO public.routes VALUES (88, 4, 5, 2234.07);
INSERT INTO public.routes VALUES (89, 4, 6, 1303.83);
INSERT INTO public.routes VALUES (90, 4, 7, 1148.10);
INSERT INTO public.routes VALUES (91, 4, 8, 1514.09);
INSERT INTO public.routes VALUES (92, 4, 10, 1163.92);
INSERT INTO public.routes VALUES (93, 4, 12, 490.17);
INSERT INTO public.routes VALUES (94, 4, 13, 1956.89);
INSERT INTO public.routes VALUES (95, 4, 14, 775.71);
INSERT INTO public.routes VALUES (96, 4, 15, 851.73);
INSERT INTO public.routes VALUES (97, 5, 4, 2234.07);
INSERT INTO public.routes VALUES (98, 5, 6, 1982.21);
INSERT INTO public.routes VALUES (99, 5, 7, 1252.27);
INSERT INTO public.routes VALUES (100, 5, 8, 813.07);
INSERT INTO public.routes VALUES (101, 5, 9, 2048.27);
INSERT INTO public.routes VALUES (102, 5, 10, 1239.65);
INSERT INTO public.routes VALUES (103, 5, 11, 2469.60);
INSERT INTO public.routes VALUES (104, 5, 14, 1678.02);
INSERT INTO public.routes VALUES (105, 5, 15, 1422.30);
INSERT INTO public.routes VALUES (106, 6, 4, 1303.83);
INSERT INTO public.routes VALUES (107, 6, 5, 1982.21);
INSERT INTO public.routes VALUES (108, 6, 7, 1654.87);
INSERT INTO public.routes VALUES (109, 6, 8, 1700.57);
INSERT INTO public.routes VALUES (110, 6, 9, 1357.77);
INSERT INTO public.routes VALUES (111, 6, 10, 1663.45);
INSERT INTO public.routes VALUES (112, 6, 11, 1464.23);
INSERT INTO public.routes VALUES (113, 6, 12, 1604.69);
INSERT INTO public.routes VALUES (114, 6, 13, 1766.10);
INSERT INTO public.routes VALUES (115, 6, 14, 1618.86);
INSERT INTO public.routes VALUES (116, 6, 15, 970.13);
INSERT INTO public.routes VALUES (117, 7, 4, 1148.10);
INSERT INTO public.routes VALUES (118, 7, 5, 1252.27);
INSERT INTO public.routes VALUES (119, 7, 6, 1654.87);
INSERT INTO public.routes VALUES (120, 7, 8, 440.34);
INSERT INTO public.routes VALUES (121, 7, 9, 920.74);
INSERT INTO public.routes VALUES (122, 7, 11, 1354.31);
INSERT INTO public.routes VALUES (123, 7, 12, 796.61);
INSERT INTO public.routes VALUES (124, 7, 13, 997.25);
INSERT INTO public.routes VALUES (125, 7, 15, 688.05);
INSERT INTO public.routes VALUES (126, 8, 4, 1514.09);
INSERT INTO public.routes VALUES (127, 8, 5, 813.07);
INSERT INTO public.routes VALUES (128, 8, 6, 1700.57);
INSERT INTO public.routes VALUES (129, 8, 7, 440.34);
INSERT INTO public.routes VALUES (130, 8, 9, 1302.74);
INSERT INTO public.routes VALUES (131, 8, 10, 427.23);
INSERT INTO public.routes VALUES (132, 8, 11, 1737.37);
INSERT INTO public.routes VALUES (133, 8, 12, 1221.77);
INSERT INTO public.routes VALUES (134, 8, 13, 566.32);
INSERT INTO public.routes VALUES (135, 8, 14, 874.10);
INSERT INTO public.routes VALUES (136, 8, 15, 834.99);
INSERT INTO public.routes VALUES (137, 9, 4, 235.29);
INSERT INTO public.routes VALUES (138, 9, 5, 2048.27);
INSERT INTO public.routes VALUES (139, 9, 6, 1357.77);
INSERT INTO public.routes VALUES (140, 9, 7, 920.74);
INSERT INTO public.routes VALUES (141, 9, 8, 1302.74);
INSERT INTO public.routes VALUES (142, 9, 10, 936.63);
INSERT INTO public.routes VALUES (143, 9, 13, 1771.74);
INSERT INTO public.routes VALUES (144, 9, 14, 540.47);
INSERT INTO public.routes VALUES (145, 9, 15, 723.45);
INSERT INTO public.routes VALUES (146, 10, 4, 1163.92);
INSERT INTO public.routes VALUES (147, 10, 5, 1239.65);
INSERT INTO public.routes VALUES (148, 10, 6, 1663.45);
INSERT INTO public.routes VALUES (149, 10, 8, 427.23);
INSERT INTO public.routes VALUES (150, 10, 9, 936.63);
INSERT INTO public.routes VALUES (151, 10, 11, 1370.21);
INSERT INTO public.routes VALUES (152, 10, 12, 811.97);
INSERT INTO public.routes VALUES (153, 10, 13, 985.64);
INSERT INTO public.routes VALUES (154, 10, 14, 454.91);
INSERT INTO public.routes VALUES (155, 10, 15, 697.67);
INSERT INTO public.routes VALUES (156, 11, 5, 2469.60);
INSERT INTO public.routes VALUES (157, 11, 6, 1464.23);
INSERT INTO public.routes VALUES (158, 11, 7, 1354.31);
INSERT INTO public.routes VALUES (159, 11, 8, 1737.37);
INSERT INTO public.routes VALUES (160, 11, 9, 435.71);
INSERT INTO public.routes VALUES (161, 11, 10, 1370.21);
INSERT INTO public.routes VALUES (162, 11, 12, 619.92);
INSERT INTO public.routes VALUES (163, 11, 13, 2192.45);
INSERT INTO public.routes VALUES (164, 11, 14, 953.33);
INSERT INTO public.routes VALUES (165, 11, 15, 1090.69);
INSERT INTO public.routes VALUES (166, 12, 4, 490.17);
INSERT INTO public.routes VALUES (167, 12, 5, 2012.63);
INSERT INTO public.routes VALUES (168, 12, 6, 1604.69);
INSERT INTO public.routes VALUES (169, 12, 7, 796.61);
INSERT INTO public.routes VALUES (170, 12, 8, 1221.77);
INSERT INTO public.routes VALUES (171, 12, 10, 811.97);
INSERT INTO public.routes VALUES (172, 12, 11, 619.92);
INSERT INTO public.routes VALUES (173, 12, 13, 1742.19);
INSERT INTO public.routes VALUES (174, 12, 14, 360.56);
INSERT INTO public.routes VALUES (175, 12, 15, 837.56);
INSERT INTO public.routes VALUES (176, 13, 2, 427.43);
INSERT INTO public.routes VALUES (177, 13, 3, 727.06);
INSERT INTO public.routes VALUES (178, 13, 4, 1956.89);
INSERT INTO public.routes VALUES (179, 13, 6, 1766.10);
INSERT INTO public.routes VALUES (180, 13, 7, 997.25);
INSERT INTO public.routes VALUES (181, 13, 8, 566.32);
INSERT INTO public.routes VALUES (182, 13, 9, 1771.74);
INSERT INTO public.routes VALUES (183, 13, 10, 985.64);
INSERT INTO public.routes VALUES (184, 13, 11, 2192.45);
INSERT INTO public.routes VALUES (185, 13, 12, 1742.19);
INSERT INTO public.routes VALUES (186, 13, 14, 1413.66);
INSERT INTO public.routes VALUES (187, 13, 15, 1149.03);
INSERT INTO public.routes VALUES (188, 14, 2, 1371.81);
INSERT INTO public.routes VALUES (189, 14, 3, 879.50);
INSERT INTO public.routes VALUES (190, 14, 4, 775.71);
INSERT INTO public.routes VALUES (191, 14, 5, 1678.02);
INSERT INTO public.routes VALUES (192, 14, 6, 1618.86);
INSERT INTO public.routes VALUES (193, 14, 8, 874.10);
INSERT INTO public.routes VALUES (194, 14, 9, 540.47);
INSERT INTO public.routes VALUES (195, 14, 10, 454.91);
INSERT INTO public.routes VALUES (196, 14, 11, 953.33);
INSERT INTO public.routes VALUES (197, 14, 12, 360.56);
INSERT INTO public.routes VALUES (198, 14, 13, 1413.66);
INSERT INTO public.routes VALUES (199, 14, 15, 703.06);
INSERT INTO public.routes VALUES (200, 15, 2, 905.32);
INSERT INTO public.routes VALUES (201, 15, 4, 851.73);
INSERT INTO public.routes VALUES (202, 15, 5, 1422.30);
INSERT INTO public.routes VALUES (203, 15, 6, 970.13);
INSERT INTO public.routes VALUES (204, 15, 7, 688.05);
INSERT INTO public.routes VALUES (205, 15, 8, 834.99);
INSERT INTO public.routes VALUES (206, 15, 9, 723.45);
INSERT INTO public.routes VALUES (207, 15, 10, 697.67);
INSERT INTO public.routes VALUES (208, 15, 11, 1090.69);
INSERT INTO public.routes VALUES (209, 15, 12, 837.56);
INSERT INTO public.routes VALUES (210, 15, 13, 1149.03);
INSERT INTO public.routes VALUES (211, 15, 14, 703.06);


--
-- TOC entry 5118 (class 0 OID 24628)
-- Dependencies: 224
-- Data for Name: units; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.units VALUES (1, '1st Infantry Battalion', 'Infantry', 1);
INSERT INTO public.units VALUES (2, '2nd Armored Regiment', 'Armored', 2);
INSERT INTO public.units VALUES (3, '3rd Artillery Brigade', 'Artillery', 3);
INSERT INTO public.units VALUES (4, '4th Logistics Battalion', 'Logistics', 4);
INSERT INTO public.units VALUES (5, '5th Engineering Regiment', 'Engineering', 5);
INSERT INTO public.units VALUES (6, '6th Signal Company', 'Signals', 6);
INSERT INTO public.units VALUES (7, '7th Medical Corps', 'Medical', 7);
INSERT INTO public.units VALUES (8, '8th Air Defense Unit', 'Air Defense', 8);
INSERT INTO public.units VALUES (9, '9th Reconnaissance Squadron', 'Reconnaissance', 9);
INSERT INTO public.units VALUES (10, '10th Transport Company', 'Transport', 10);


--
-- TOC entry 5114 (class 0 OID 24596)
-- Dependencies: 220
-- Data for Name: vehicle_types; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.vehicle_types VALUES (1, 'Cargo Truck', 60.00, 10000.00, 300.00, 0.30);
INSERT INTO public.vehicle_types VALUES (2, 'Fuel Tanker', 55.00, 15000.00, 500.00, 0.45);
INSERT INTO public.vehicle_types VALUES (3, 'Water Tanker', 55.00, 12000.00, 400.00, 0.40);
INSERT INTO public.vehicle_types VALUES (4, 'Light Tactical Vehicle', 90.00, 1000.00, 120.00, 0.15);
INSERT INTO public.vehicle_types VALUES (5, 'Armored Personnel Carrier', 70.00, 3000.00, 600.00, 0.80);
INSERT INTO public.vehicle_types VALUES (6, 'Infantry Fighting Vehicle', 65.00, 2500.00, 700.00, 0.90);
INSERT INTO public.vehicle_types VALUES (7, 'Main Battle Tank', 45.00, 1000.00, 1200.00, 3.50);
INSERT INTO public.vehicle_types VALUES (8, 'Ambulance', 80.00, 500.00, 150.00, 0.20);
INSERT INTO public.vehicle_types VALUES (9, 'Recovery Vehicle', 50.00, 5000.00, 800.00, 1.20);
INSERT INTO public.vehicle_types VALUES (10, 'Heavy Equipment Transporter', 50.00, 60000.00, 1000.00, 1.50);
INSERT INTO public.vehicle_types VALUES (11, 'Mobile Command Vehicle', 70.00, 2000.00, 300.00, 0.35);
INSERT INTO public.vehicle_types VALUES (12, 'Engineering Vehicle', 40.00, 5000.00, 900.00, 1.50);


--
-- TOC entry 5120 (class 0 OID 24644)
-- Dependencies: 226
-- Data for Name: vehicles; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.vehicles VALUES (8, 'MH-TRK-001', 'Cargo Truck Alpha', 1, 250.00, 1, 4);
INSERT INTO public.vehicles VALUES (9, 'MH-TRK-002', 'Cargo Truck Bravo', 1, 180.00, 2, 4);
INSERT INTO public.vehicles VALUES (10, 'MH-TRK-003', 'Cargo Truck Charlie', 1, 300.00, 3, 4);
INSERT INTO public.vehicles VALUES (11, 'MH-FTK-001', 'Fuel Tanker One', 2, 400.00, 4, 4);
INSERT INTO public.vehicles VALUES (12, 'MH-WTK-001', 'Water Tanker One', 3, 350.00, 5, 3);
INSERT INTO public.vehicles VALUES (13, 'MH-LTV-001', 'Tactical Vehicle One', 4, 100.00, 1, 1);
INSERT INTO public.vehicles VALUES (14, 'MH-APC-001', 'APC Falcon', 5, 500.00, 2, 2);
INSERT INTO public.vehicles VALUES (15, 'MH-APC-002', 'APC Eagle', 5, 480.00, 3, 2);
INSERT INTO public.vehicles VALUES (16, 'MH-IFV-001', 'IFV Tiger', 6, 650.00, 4, 2);
INSERT INTO public.vehicles VALUES (17, 'MH-MBT-001', 'Tank Panther', 7, 900.00, 5, 2);
INSERT INTO public.vehicles VALUES (18, 'MH-AMB-001', 'Medical One', 8, 120.00, 6, 7);
INSERT INTO public.vehicles VALUES (19, 'MH-AMB-002', 'Medical Two', 8, 140.00, 7, 7);
INSERT INTO public.vehicles VALUES (20, 'MH-REC-001', 'Recovery Eagle', 9, 700.00, 7, 5);
INSERT INTO public.vehicles VALUES (21, 'MH-HET-001', 'Heavy Transporter One', 10, 800.00, 8, 4);
INSERT INTO public.vehicles VALUES (22, 'MH-MCV-001', 'Command Vehicle Alpha', 11, 280.00, 9, 6);


--
-- TOC entry 5132 (class 0 OID 24843)
-- Dependencies: 238
-- Data for Name: trips; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.trips VALUES (1, 1, 'MH-TRK-001', 1, 1, '00:15:00', '02:15:00', 500.00, 1);
INSERT INTO public.trips VALUES (2, 1, 'MH-APC-001', 4, 5, '00:30:00', '01:30:00', 200.00, 2);
INSERT INTO public.trips VALUES (3, 1, 'MH-LTV-001', 7, 4, '01:00:00', '02:00:00', 300.00, 1);
INSERT INTO public.trips VALUES (4, 2, 'MH-TRK-001', 2, 1, '00:10:00', '05:00:00', 600.00, 4);
INSERT INTO public.trips VALUES (5, 2, 'MH-TRK-002', 4, 6, '00:30:00', '04:30:00', 550.00, 4);
INSERT INTO public.trips VALUES (6, 2, 'MH-APC-001', 1, 2, '01:00:00', '02:15:00', 300.00, 2);
INSERT INTO public.trips VALUES (7, 2, 'MH-IFV-001', 3, 3, '01:20:00', '03:30:00', 700.00, 3);
INSERT INTO public.trips VALUES (8, 3, 'MH-AMB-001', 7, 3, '00:10:00', '01:20:00', 100.00, 7);
INSERT INTO public.trips VALUES (9, 3, 'MH-APC-002', 13, 3, '00:20:00', '01:40:00', 120.00, 7);
INSERT INTO public.trips VALUES (10, 4, 'MH-FTK-001', 5, 2, '00:00:00', '03:00:00', 800.00, 4);
INSERT INTO public.trips VALUES (11, 4, 'MH-TRK-003', 14, 6, '00:30:00', '02:30:00', 400.00, 3);
INSERT INTO public.trips VALUES (12, 5, 'MH-MBT-001', 2, 1, '00:00:00', '06:00:00', 500.00, 2);
INSERT INTO public.trips VALUES (13, 5, 'MH-APC-001', 9, 5, '00:30:00', '04:00:00', 300.00, 9);
INSERT INTO public.trips VALUES (14, 5, 'MH-MCV-001', 10, 5, '01:00:00', '02:00:00', 150.00, 6);
INSERT INTO public.trips VALUES (15, 6, 'MH-TRK-001', 1, 4, '00:00:00', '02:00:00', 300.00, 4);
INSERT INTO public.trips VALUES (16, 6, 'MH-TRK-001', 4, 6, '00:30:00', '01:30:00', 200.00, 3);
INSERT INTO public.trips VALUES (17, 7, 'MH-APC-001', 2, 1, '00:10:00', '02:00:00', 150.00, 2);
INSERT INTO public.trips VALUES (18, 7, 'MH-APC-001', 9, 5, '00:30:00', '01:30:00', 100.00, 9);


--
-- TOC entry 5133 (class 0 OID 24885)
-- Dependencies: 239
-- Data for Name: trip_crew; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.trip_crew VALUES (1, 1);
INSERT INTO public.trip_crew VALUES (1, 4);
INSERT INTO public.trip_crew VALUES (2, 2);
INSERT INTO public.trip_crew VALUES (2, 3);
INSERT INTO public.trip_crew VALUES (3, 9);
INSERT INTO public.trip_crew VALUES (3, 7);
INSERT INTO public.trip_crew VALUES (4, 13);
INSERT INTO public.trip_crew VALUES (4, 5);
INSERT INTO public.trip_crew VALUES (5, 19);
INSERT INTO public.trip_crew VALUES (5, 6);
INSERT INTO public.trip_crew VALUES (6, 10);
INSERT INTO public.trip_crew VALUES (6, 17);
INSERT INTO public.trip_crew VALUES (7, 2);
INSERT INTO public.trip_crew VALUES (7, 3);
INSERT INTO public.trip_crew VALUES (7, 8);
INSERT INTO public.trip_crew VALUES (8, 9);
INSERT INTO public.trip_crew VALUES (8, 12);
INSERT INTO public.trip_crew VALUES (9, 20);
INSERT INTO public.trip_crew VALUES (9, 11);
INSERT INTO public.trip_crew VALUES (10, 1);
INSERT INTO public.trip_crew VALUES (10, 14);
INSERT INTO public.trip_crew VALUES (11, 13);
INSERT INTO public.trip_crew VALUES (11, 15);
INSERT INTO public.trip_crew VALUES (12, 10);
INSERT INTO public.trip_crew VALUES (12, 17);
INSERT INTO public.trip_crew VALUES (12, 18);
INSERT INTO public.trip_crew VALUES (13, 2);
INSERT INTO public.trip_crew VALUES (13, 3);
INSERT INTO public.trip_crew VALUES (14, 20);
INSERT INTO public.trip_crew VALUES (14, 16);
INSERT INTO public.trip_crew VALUES (15, 13);
INSERT INTO public.trip_crew VALUES (15, 14);
INSERT INTO public.trip_crew VALUES (16, 19);
INSERT INTO public.trip_crew VALUES (16, 11);
INSERT INTO public.trip_crew VALUES (17, 1);
INSERT INTO public.trip_crew VALUES (17, 2);
INSERT INTO public.trip_crew VALUES (18, 5);
INSERT INTO public.trip_crew VALUES (18, 7);


--
-- TOC entry 5137 (class 0 OID 24937)
-- Dependencies: 243
-- Data for Name: vehicle_availability; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.vehicle_availability VALUES (1, 'MH-TRK-001', 'Scheduled Maintenance', '2026-06-10 09:00:00', '2026-06-10 12:00:00');
INSERT INTO public.vehicle_availability VALUES (2, 'MH-TRK-002', 'Fuel Refill', '2026-06-11 10:00:00', '2026-06-11 13:00:00');
INSERT INTO public.vehicle_availability VALUES (3, 'MH-APC-001', 'Engine Overhaul', '2026-06-12 08:00:00', '2026-06-12 11:00:00');
INSERT INTO public.vehicle_availability VALUES (4, 'MH-IFV-001', 'Training Use', '2026-06-13 14:00:00', '2026-06-13 17:00:00');
INSERT INTO public.vehicle_availability VALUES (5, 'MH-MBT-001', 'Armor Inspection', '2026-06-14 09:00:00', '2026-06-14 12:00:00');
INSERT INTO public.vehicle_availability VALUES (6, 'MH-AMB-001', 'Medical Deployment', '2026-06-10 15:00:00', '2026-06-10 18:00:00');
INSERT INTO public.vehicle_availability VALUES (7, 'MH-FTK-001', 'Pressure Test', '2026-06-11 06:00:00', '2026-06-11 09:00:00');
INSERT INTO public.vehicle_availability VALUES (8, 'MH-TRK-003', 'Tyre Replacement', '2026-06-12 13:00:00', '2026-06-12 16:00:00');
INSERT INTO public.vehicle_availability VALUES (9, 'MH-APC-002', 'Weapon Systems Check', '2026-06-13 09:00:00', '2026-06-13 12:00:00');
INSERT INTO public.vehicle_availability VALUES (10, 'MH-MCV-001', 'Comms Equipment Upgrade', '2026-06-15 08:00:00', '2026-06-15 14:00:00');


--
-- TOC entry 5143 (class 0 OID 0)
-- Dependencies: 227
-- Name: crew_types_crew_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crew_types_crew_type_id_seq', 12, true);


--
-- TOC entry 5144 (class 0 OID 0)
-- Dependencies: 240
-- Name: individual_availability_availability_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.individual_availability_availability_id_seq', 5, true);


--
-- TOC entry 5145 (class 0 OID 0)
-- Dependencies: 229
-- Name: individuals_individual_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.individuals_individual_id_seq', 10, true);


--
-- TOC entry 5146 (class 0 OID 0)
-- Dependencies: 233
-- Name: load_types_load_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.load_types_load_type_id_seq', 10, true);


--
-- TOC entry 5147 (class 0 OID 0)
-- Dependencies: 221
-- Name: locations_location_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.locations_location_id_seq', 15, true);


--
-- TOC entry 5148 (class 0 OID 0)
-- Dependencies: 235
-- Name: plans_plan_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.plans_plan_id_seq', 3, true);


--
-- TOC entry 5149 (class 0 OID 0)
-- Dependencies: 231
-- Name: routes_route_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.routes_route_id_seq', 211, true);


--
-- TOC entry 5150 (class 0 OID 0)
-- Dependencies: 237
-- Name: trips_trip_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.trips_trip_id_seq', 15, true);


--
-- TOC entry 5151 (class 0 OID 0)
-- Dependencies: 223
-- Name: units_unit_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.units_unit_id_seq', 10, true);


--
-- TOC entry 5152 (class 0 OID 0)
-- Dependencies: 242
-- Name: vehicle_availability_availability_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vehicle_availability_availability_id_seq', 7, true);


--
-- TOC entry 5153 (class 0 OID 0)
-- Dependencies: 219
-- Name: vehicle_types_vehicle_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vehicle_types_vehicle_type_id_seq', 12, true);


--
-- TOC entry 5154 (class 0 OID 0)
-- Dependencies: 225
-- Name: vehicles_vehicle_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vehicles_vehicle_id_seq', 22, true);


-- Completed on 2026-06-09 12:45:58

--
-- PostgreSQL database dump complete
--

\unrestrict AVFuLS9jBZdVTw2gLphJbHwfuHGceW5zHoNYSBU98mMr3XTubLaqRQzQVnj0TMW

