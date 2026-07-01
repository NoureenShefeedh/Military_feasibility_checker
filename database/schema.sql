--
-- PostgreSQL database dump
--

\restrict Wz70pCGj53rmfCDQqRmPTnmUZuYceaRIEvDTAjgXkHviFXuYcejmc4axwy8kSbS

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

-- Started on 2026-06-09 12:38:55

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 228 (class 1259 OID 24674)
-- Name: crew_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crew_types (
    crew_type_id integer NOT NULL,
    crew_type_name character varying(100) NOT NULL
);


ALTER TABLE public.crew_types OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 24673)
-- Name: crew_types_crew_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crew_types_crew_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crew_types_crew_type_id_seq OWNER TO postgres;

--
-- TOC entry 5131 (class 0 OID 0)
-- Dependencies: 227
-- Name: crew_types_crew_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crew_types_crew_type_id_seq OWNED BY public.crew_types.crew_type_id;


--
-- TOC entry 241 (class 1259 OID 24916)
-- Name: individual_availability; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.individual_availability (
    availability_id integer NOT NULL,
    individual_id integer,
    reason character varying(200),
    not_available_from timestamp without time zone,
    not_available_to timestamp without time zone
);


ALTER TABLE public.individual_availability OWNER TO postgres;

--
-- TOC entry 240 (class 1259 OID 24915)
-- Name: individual_availability_availability_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.individual_availability_availability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.individual_availability_availability_id_seq OWNER TO postgres;

--
-- TOC entry 5132 (class 0 OID 0)
-- Dependencies: 240
-- Name: individual_availability_availability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.individual_availability_availability_id_seq OWNED BY public.individual_availability.availability_id;


--
-- TOC entry 230 (class 1259 OID 24702)
-- Name: individuals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.individuals (
    individual_id integer NOT NULL,
    name character varying(100) NOT NULL,
    crew_type_id integer NOT NULL,
    current_location_id integer
);


ALTER TABLE public.individuals OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 24701)
-- Name: individuals_individual_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.individuals_individual_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.individuals_individual_id_seq OWNER TO postgres;

--
-- TOC entry 5133 (class 0 OID 0)
-- Dependencies: 229
-- Name: individuals_individual_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.individuals_individual_id_seq OWNED BY public.individuals.individual_id;


--
-- TOC entry 234 (class 1259 OID 24746)
-- Name: load_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.load_types (
    load_type_id integer NOT NULL,
    load_type_name character varying(100) NOT NULL,
    height numeric(10,2),
    width numeric(10,2),
    length numeric(10,2),
    weight numeric(10,2),
    volume numeric(10,2)
);


ALTER TABLE public.load_types OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 24745)
-- Name: load_types_load_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.load_types_load_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.load_types_load_type_id_seq OWNER TO postgres;

--
-- TOC entry 5134 (class 0 OID 0)
-- Dependencies: 233
-- Name: load_types_load_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.load_types_load_type_id_seq OWNED BY public.load_types.load_type_id;


--
-- TOC entry 222 (class 1259 OID 24617)
-- Name: locations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.locations (
    location_id integer NOT NULL,
    location_name character varying(100) NOT NULL,
    latitude numeric(10,8) NOT NULL,
    longitude numeric(11,8) NOT NULL
);


ALTER TABLE public.locations OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 24616)
-- Name: locations_location_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.locations_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.locations_location_id_seq OWNER TO postgres;

--
-- TOC entry 5135 (class 0 OID 0)
-- Dependencies: 221
-- Name: locations_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.locations_location_id_seq OWNED BY public.locations.location_id;


--
-- TOC entry 236 (class 1259 OID 24831)
-- Name: plans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.plans (
    plan_id integer NOT NULL,
    plan_name character varying(100) NOT NULL,
    num_of_vehicles integer NOT NULL,
    default_start_time time without time zone CONSTRAINT plans_earliest_start_time_not_null NOT NULL,
    total_fuel numeric(12,2)
);


ALTER TABLE public.plans OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 24830)
-- Name: plans_plan_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.plans_plan_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.plans_plan_id_seq OWNER TO postgres;

--
-- TOC entry 5136 (class 0 OID 0)
-- Dependencies: 235
-- Name: plans_plan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.plans_plan_id_seq OWNED BY public.plans.plan_id;


--
-- TOC entry 232 (class 1259 OID 24724)
-- Name: routes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.routes (
    route_id integer NOT NULL,
    start_location_id integer NOT NULL,
    end_location_id integer NOT NULL,
    distance numeric(10,2) NOT NULL,
    CONSTRAINT routes_check CHECK ((start_location_id <> end_location_id))
);


ALTER TABLE public.routes OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 24723)
-- Name: routes_route_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.routes_route_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.routes_route_id_seq OWNER TO postgres;

--
-- TOC entry 5137 (class 0 OID 0)
-- Dependencies: 231
-- Name: routes_route_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.routes_route_id_seq OWNED BY public.routes.route_id;


--
-- TOC entry 239 (class 1259 OID 24885)
-- Name: trip_crew; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trip_crew (
    trip_id integer NOT NULL,
    individual_id integer NOT NULL
);


ALTER TABLE public.trip_crew OWNER TO postgres;

--
-- TOC entry 238 (class 1259 OID 24843)
-- Name: trips; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trips (
    trip_id integer NOT NULL,
    plan_id integer NOT NULL,
    vehicle_number character varying(50) NOT NULL,
    route_id integer NOT NULL,
    load_type_id integer NOT NULL,
    start_offset time without time zone CONSTRAINT trips_start_time_not_null NOT NULL,
    duration time without time zone CONSTRAINT trips_end_time_not_null NOT NULL,
    quantity_of_load numeric(10,2) NOT NULL,
    unit_id integer NOT NULL
);


ALTER TABLE public.trips OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 24842)
-- Name: trips_trip_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.trips_trip_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trips_trip_id_seq OWNER TO postgres;

--
-- TOC entry 5138 (class 0 OID 0)
-- Dependencies: 237
-- Name: trips_trip_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.trips_trip_id_seq OWNED BY public.trips.trip_id;


--
-- TOC entry 224 (class 1259 OID 24628)
-- Name: units; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.units (
    unit_id integer NOT NULL,
    unit_name character varying(100) NOT NULL,
    unit_type character varying(50) NOT NULL,
    location_id integer NOT NULL
);


ALTER TABLE public.units OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 24627)
-- Name: units_unit_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.units_unit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.units_unit_id_seq OWNER TO postgres;

--
-- TOC entry 5139 (class 0 OID 0)
-- Dependencies: 223
-- Name: units_unit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.units_unit_id_seq OWNED BY public.units.unit_id;


--
-- TOC entry 243 (class 1259 OID 24937)
-- Name: vehicle_availability; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_availability (
    availability_id integer NOT NULL,
    vehicle_number character varying(20),
    reason character varying(200),
    not_available_from timestamp without time zone,
    not_available_to timestamp without time zone
);


ALTER TABLE public.vehicle_availability OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 24936)
-- Name: vehicle_availability_availability_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vehicle_availability_availability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicle_availability_availability_id_seq OWNER TO postgres;

--
-- TOC entry 5140 (class 0 OID 0)
-- Dependencies: 242
-- Name: vehicle_availability_availability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehicle_availability_availability_id_seq OWNED BY public.vehicle_availability.availability_id;


--
-- TOC entry 220 (class 1259 OID 24596)
-- Name: vehicle_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_types (
    vehicle_type_id integer NOT NULL,
    type_name character varying(100) NOT NULL,
    default_speed numeric(6,2),
    max_load_capacity numeric(10,2),
    fuel_capacity numeric(10,2),
    fuel_consumption_rate numeric(10,2)
);


ALTER TABLE public.vehicle_types OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 24595)
-- Name: vehicle_types_vehicle_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vehicle_types_vehicle_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicle_types_vehicle_type_id_seq OWNER TO postgres;

--
-- TOC entry 5141 (class 0 OID 0)
-- Dependencies: 219
-- Name: vehicle_types_vehicle_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehicle_types_vehicle_type_id_seq OWNED BY public.vehicle_types.vehicle_type_id;


--
-- TOC entry 226 (class 1259 OID 24644)
-- Name: vehicles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicles (
    vehicle_id integer NOT NULL,
    vehicle_number character varying(50) NOT NULL,
    vehicle_name character varying(100) NOT NULL,
    vehicle_type_id integer NOT NULL,
    current_fuel_level numeric(10,2),
    current_location_id integer,
    unit_id integer NOT NULL
);


ALTER TABLE public.vehicles OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 24643)
-- Name: vehicles_vehicle_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vehicles_vehicle_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicles_vehicle_id_seq OWNER TO postgres;

--
-- TOC entry 5142 (class 0 OID 0)
-- Dependencies: 225
-- Name: vehicles_vehicle_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehicles_vehicle_id_seq OWNED BY public.vehicles.vehicle_id;


--
-- TOC entry 4919 (class 2604 OID 24677)
-- Name: crew_types crew_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crew_types ALTER COLUMN crew_type_id SET DEFAULT nextval('public.crew_types_crew_type_id_seq'::regclass);


--
-- TOC entry 4925 (class 2604 OID 24919)
-- Name: individual_availability availability_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.individual_availability ALTER COLUMN availability_id SET DEFAULT nextval('public.individual_availability_availability_id_seq'::regclass);


--
-- TOC entry 4920 (class 2604 OID 24705)
-- Name: individuals individual_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.individuals ALTER COLUMN individual_id SET DEFAULT nextval('public.individuals_individual_id_seq'::regclass);


--
-- TOC entry 4922 (class 2604 OID 24749)
-- Name: load_types load_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.load_types ALTER COLUMN load_type_id SET DEFAULT nextval('public.load_types_load_type_id_seq'::regclass);


--
-- TOC entry 4916 (class 2604 OID 24620)
-- Name: locations location_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.locations ALTER COLUMN location_id SET DEFAULT nextval('public.locations_location_id_seq'::regclass);


--
-- TOC entry 4923 (class 2604 OID 24834)
-- Name: plans plan_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.plans ALTER COLUMN plan_id SET DEFAULT nextval('public.plans_plan_id_seq'::regclass);


--
-- TOC entry 4921 (class 2604 OID 24727)
-- Name: routes route_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.routes ALTER COLUMN route_id SET DEFAULT nextval('public.routes_route_id_seq'::regclass);


--
-- TOC entry 4924 (class 2604 OID 24846)
-- Name: trips trip_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trips ALTER COLUMN trip_id SET DEFAULT nextval('public.trips_trip_id_seq'::regclass);


--
-- TOC entry 4917 (class 2604 OID 24631)
-- Name: units unit_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.units ALTER COLUMN unit_id SET DEFAULT nextval('public.units_unit_id_seq'::regclass);


--
-- TOC entry 4926 (class 2604 OID 24940)
-- Name: vehicle_availability availability_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_availability ALTER COLUMN availability_id SET DEFAULT nextval('public.vehicle_availability_availability_id_seq'::regclass);


--
-- TOC entry 4915 (class 2604 OID 24599)
-- Name: vehicle_types vehicle_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_types ALTER COLUMN vehicle_type_id SET DEFAULT nextval('public.vehicle_types_vehicle_type_id_seq'::regclass);


--
-- TOC entry 4918 (class 2604 OID 24647)
-- Name: vehicles vehicle_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles ALTER COLUMN vehicle_id SET DEFAULT nextval('public.vehicles_vehicle_id_seq'::regclass);


--
-- TOC entry 4941 (class 2606 OID 24683)
-- Name: crew_types crew_types_crew_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crew_types
    ADD CONSTRAINT crew_types_crew_type_name_key UNIQUE (crew_type_name);


--
-- TOC entry 4943 (class 2606 OID 24681)
-- Name: crew_types crew_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crew_types
    ADD CONSTRAINT crew_types_pkey PRIMARY KEY (crew_type_id);


--
-- TOC entry 4959 (class 2606 OID 24922)
-- Name: individual_availability individual_availability_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.individual_availability
    ADD CONSTRAINT individual_availability_pkey PRIMARY KEY (availability_id);


--
-- TOC entry 4945 (class 2606 OID 24711)
-- Name: individuals individuals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.individuals
    ADD CONSTRAINT individuals_pkey PRIMARY KEY (individual_id);


--
-- TOC entry 4949 (class 2606 OID 24755)
-- Name: load_types load_types_load_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.load_types
    ADD CONSTRAINT load_types_load_type_name_key UNIQUE (load_type_name);


--
-- TOC entry 4951 (class 2606 OID 24753)
-- Name: load_types load_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.load_types
    ADD CONSTRAINT load_types_pkey PRIMARY KEY (load_type_id);


--
-- TOC entry 4933 (class 2606 OID 24626)
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (location_id);


--
-- TOC entry 4953 (class 2606 OID 24841)
-- Name: plans plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_pkey PRIMARY KEY (plan_id);


--
-- TOC entry 4947 (class 2606 OID 24734)
-- Name: routes routes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT routes_pkey PRIMARY KEY (route_id);


--
-- TOC entry 4957 (class 2606 OID 24891)
-- Name: trip_crew trip_crew_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip_crew
    ADD CONSTRAINT trip_crew_pkey PRIMARY KEY (trip_id, individual_id);


--
-- TOC entry 4955 (class 2606 OID 24859)
-- Name: trips trips_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trips
    ADD CONSTRAINT trips_pkey PRIMARY KEY (trip_id);


--
-- TOC entry 4935 (class 2606 OID 24637)
-- Name: units units_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_pkey PRIMARY KEY (unit_id);


--
-- TOC entry 4961 (class 2606 OID 24943)
-- Name: vehicle_availability vehicle_availability_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_availability
    ADD CONSTRAINT vehicle_availability_pkey PRIMARY KEY (availability_id);


--
-- TOC entry 4929 (class 2606 OID 24603)
-- Name: vehicle_types vehicle_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_types
    ADD CONSTRAINT vehicle_types_pkey PRIMARY KEY (vehicle_type_id);


--
-- TOC entry 4931 (class 2606 OID 24605)
-- Name: vehicle_types vehicle_types_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_types
    ADD CONSTRAINT vehicle_types_type_name_key UNIQUE (type_name);


--
-- TOC entry 4937 (class 2606 OID 24655)
-- Name: vehicles vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_pkey PRIMARY KEY (vehicle_id);


--
-- TOC entry 4939 (class 2606 OID 24657)
-- Name: vehicles vehicles_vehicle_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_vehicle_number_key UNIQUE (vehicle_number);


--
-- TOC entry 4977 (class 2606 OID 24923)
-- Name: individual_availability individual_availability_individual_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.individual_availability
    ADD CONSTRAINT individual_availability_individual_id_fkey FOREIGN KEY (individual_id) REFERENCES public.individuals(individual_id);


--
-- TOC entry 4966 (class 2606 OID 24712)
-- Name: individuals individuals_crew_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.individuals
    ADD CONSTRAINT individuals_crew_type_id_fkey FOREIGN KEY (crew_type_id) REFERENCES public.crew_types(crew_type_id);


--
-- TOC entry 4967 (class 2606 OID 24717)
-- Name: individuals individuals_current_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.individuals
    ADD CONSTRAINT individuals_current_location_id_fkey FOREIGN KEY (current_location_id) REFERENCES public.locations(location_id);


--
-- TOC entry 4968 (class 2606 OID 24740)
-- Name: routes routes_end_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT routes_end_location_id_fkey FOREIGN KEY (end_location_id) REFERENCES public.locations(location_id);


--
-- TOC entry 4969 (class 2606 OID 24735)
-- Name: routes routes_start_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT routes_start_location_id_fkey FOREIGN KEY (start_location_id) REFERENCES public.locations(location_id);


--
-- TOC entry 4975 (class 2606 OID 24897)
-- Name: trip_crew trip_crew_individual_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip_crew
    ADD CONSTRAINT trip_crew_individual_id_fkey FOREIGN KEY (individual_id) REFERENCES public.individuals(individual_id);


--
-- TOC entry 4976 (class 2606 OID 24892)
-- Name: trip_crew trip_crew_trip_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip_crew
    ADD CONSTRAINT trip_crew_trip_id_fkey FOREIGN KEY (trip_id) REFERENCES public.trips(trip_id);


--
-- TOC entry 4970 (class 2606 OID 24875)
-- Name: trips trips_load_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trips
    ADD CONSTRAINT trips_load_type_id_fkey FOREIGN KEY (load_type_id) REFERENCES public.load_types(load_type_id);


--
-- TOC entry 4971 (class 2606 OID 24860)
-- Name: trips trips_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trips
    ADD CONSTRAINT trips_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(plan_id);


--
-- TOC entry 4972 (class 2606 OID 24870)
-- Name: trips trips_route_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trips
    ADD CONSTRAINT trips_route_id_fkey FOREIGN KEY (route_id) REFERENCES public.routes(route_id);


--
-- TOC entry 4973 (class 2606 OID 24880)
-- Name: trips trips_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trips
    ADD CONSTRAINT trips_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(unit_id);


--
-- TOC entry 4974 (class 2606 OID 24865)
-- Name: trips trips_vehicle_number_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trips
    ADD CONSTRAINT trips_vehicle_number_fkey FOREIGN KEY (vehicle_number) REFERENCES public.vehicles(vehicle_number);


--
-- TOC entry 4962 (class 2606 OID 24638)
-- Name: units units_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(location_id);


--
-- TOC entry 4978 (class 2606 OID 24944)
-- Name: vehicle_availability vehicle_availability_vehicle_number_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_availability
    ADD CONSTRAINT vehicle_availability_vehicle_number_fkey FOREIGN KEY (vehicle_number) REFERENCES public.vehicles(vehicle_number);


--
-- TOC entry 4963 (class 2606 OID 24663)
-- Name: vehicles vehicles_current_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_current_location_id_fkey FOREIGN KEY (current_location_id) REFERENCES public.locations(location_id);


--
-- TOC entry 4964 (class 2606 OID 24668)
-- Name: vehicles vehicles_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(unit_id);


--
-- TOC entry 4965 (class 2606 OID 24658)
-- Name: vehicles vehicles_vehicle_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_vehicle_type_id_fkey FOREIGN KEY (vehicle_type_id) REFERENCES public.vehicle_types(vehicle_type_id);


-- Completed on 2026-06-09 12:38:56

--
-- PostgreSQL database dump complete
--

\unrestrict Wz70pCGj53rmfCDQqRmPTnmUZuYceaRIEvDTAjgXkHviFXuYcejmc4axwy8kSbS

ALTER TABLE public.locations
ADD COLUMN has_fuel_station boolean DEFAULT false;

CREATE TYPE public.plan_priority AS ENUM ('low', 'medium', 'high');

ALTER TABLE public.plans
ADD COLUMN priority public.plan_priority NOT NULL DEFAULT 'medium';

CREATE OR REPLACE FUNCTION cleanup_expired_availability()

RETURNS VOID LANGUAGE plpgsql AS $$

BEGIN

  DELETE FROM vehicle_availability WHERE not_available_to <= NOW();

  DELETE FROM individual_availability WHERE not_available_to <= NOW();

END;

$$;