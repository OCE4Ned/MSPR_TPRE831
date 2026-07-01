CREATE DATABASE airflow;

\connect industrial_dw

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS bronze.raw_events (
    id BIGSERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_system TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    payload_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS silver.cleaned_events (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    source_file TEXT NOT NULL,
    source_system TEXT NOT NULL,
    payload JSONB NOT NULL,
    cleaned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS silver.sensor_events (
    id BIGSERIAL PRIMARY KEY,
    bronze_event_id BIGINT NOT NULL REFERENCES bronze.raw_events(id),
    event_ts TIMESTAMPTZ,
    machine_id TEXT,
    cycle_time_sec NUMERIC,
    temperature_c NUMERIC,
    vibration_mms NUMERIC,
    sound_db NUMERIC,
    oil_level_pct NUMERIC,
    coolant_level_pct NUMERIC,
    hydraulic_pressure_bar NUMERIC,
    coolant_flow_l_min NUMERIC,
    heat_index NUMERIC,
    power_consumption_kw NUMERIC,
    operational_hours NUMERIC,
    error_codes_last_30_days INTEGER,
    remaining_useful_life_days NUMERIC,
    predicted_failure_probability NUMERIC,
    sensor_anomaly_score NUMERIC,
    ai_override_events INTEGER,
    failure_within_7_days INTEGER,
    quality_status TEXT,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (bronze_event_id)
);

CREATE TABLE IF NOT EXISTS silver.logistics_events (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    event_ts TIMESTAMPTZ,
    supplier_id TEXT,
    raw_material_id TEXT,
    warehouse_id TEXT,
    delivery_status TEXT,
    stock_level NUMERIC,
    available_stock_qty NUMERIC,
    stockout_flag BOOLEAN,
    payload JSONB NOT NULL,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.machine_health_daily (
    snapshot_date DATE NOT NULL,
    machine_id TEXT NOT NULL,
    event_count INTEGER NOT NULL,
    avg_temperature_c NUMERIC,
    avg_vibration_mms NUMERIC,
    avg_power_consumption_kw NUMERIC,
    avg_sensor_anomaly_score NUMERIC,
    failure_alerts INTEGER NOT NULL,
    high_risk_events INTEGER NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (snapshot_date, machine_id)
);

CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_id INTEGER PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    week INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.dim_plant (
    plant_id TEXT PRIMARY KEY,
    plant_name TEXT,
    country TEXT
);

CREATE TABLE IF NOT EXISTS gold.dim_line (
    production_line_id TEXT PRIMARY KEY,
    plant_id TEXT REFERENCES gold.dim_plant(plant_id),
    line_name TEXT
);

CREATE TABLE IF NOT EXISTS gold.dim_shift (
    shift_id TEXT PRIMARY KEY,
    shift_name TEXT NOT NULL,
    start_hour TEXT NOT NULL,
    end_hour TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.dim_product (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    product_family TEXT
);

CREATE TABLE IF NOT EXISTS gold.dim_defect (
    defect_id TEXT PRIMARY KEY,
    defect_type TEXT,
    defect_category TEXT,
    defect_severity TEXT
);

CREATE TABLE IF NOT EXISTS gold.dim_machine (
    machine_id TEXT PRIMARY KEY,
    production_line_id TEXT REFERENCES gold.dim_line(production_line_id),
    machine_type TEXT,
    installation_year INTEGER
);

CREATE TABLE IF NOT EXISTS gold.dim_supplier (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.dim_raw_material (
    raw_material_id TEXT PRIMARY KEY,
    raw_material_name TEXT NOT NULL,
    supplier_id TEXT REFERENCES gold.dim_supplier(supplier_id)
);

CREATE TABLE IF NOT EXISTS gold.dim_warehouse (
    warehouse_id TEXT PRIMARY KEY,
    plant_id TEXT REFERENCES gold.dim_plant(plant_id)
);

CREATE TABLE IF NOT EXISTS gold.dim_customer (
    customer_id TEXT PRIMARY KEY,
    customer_region TEXT
);

CREATE TABLE IF NOT EXISTS gold.fact_production (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    date_id INTEGER REFERENCES gold.dim_date(date_id),
    plant_id TEXT REFERENCES gold.dim_plant(plant_id),
    production_line_id TEXT REFERENCES gold.dim_line(production_line_id),
    machine_id TEXT REFERENCES gold.dim_machine(machine_id),
    product_id TEXT REFERENCES gold.dim_product(product_id),
    shift_id TEXT REFERENCES gold.dim_shift(shift_id),
    planned_production_qty INTEGER,
    actual_production_qty INTEGER,
    good_qty INTEGER,
    scrap_qty INTEGER,
    cycle_time_sec NUMERIC,
    target_cycle_time_sec NUMERIC,
    production_speed NUMERIC,
    downtime_minutes NUMERIC,
    setup_time_minutes NUMERIC,
    availability_rate NUMERIC,
    performance_rate NUMERIC,
    quality_rate NUMERIC,
    trs NUMERIC,
    scrap_rate NUMERIC
);

CREATE TABLE IF NOT EXISTS gold.fact_quality (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    date_id INTEGER REFERENCES gold.dim_date(date_id),
    machine_id TEXT REFERENCES gold.dim_machine(machine_id),
    product_id TEXT REFERENCES gold.dim_product(product_id),
    defect_id TEXT REFERENCES gold.dim_defect(defect_id),
    dimension_measurement NUMERIC,
    tolerance_min NUMERIC,
    tolerance_max NUMERIC,
    is_conforming BOOLEAN,
    scrap_flag BOOLEAN,
    rework_required BOOLEAN,
    quality_score NUMERIC
);

CREATE TABLE IF NOT EXISTS gold.fact_maintenance (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    date_id INTEGER REFERENCES gold.dim_date(date_id),
    machine_id TEXT REFERENCES gold.dim_machine(machine_id),
    maintenance_event_id TEXT,
    maintenance_type TEXT,
    failure_type TEXT,
    failure_code TEXT,
    failure_severity TEXT,
    repair_time_minutes NUMERIC,
    downtime_minutes NUMERIC,
    maintenance_cost NUMERIC,
    predicted_failure_probability NUMERIC,
    sensor_anomaly_score NUMERIC
);

CREATE TABLE IF NOT EXISTS gold.fact_energy (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    date_id INTEGER REFERENCES gold.dim_date(date_id),
    machine_id TEXT REFERENCES gold.dim_machine(machine_id),
    energy_consumption_kwh NUMERIC,
    compressed_air_usage NUMERIC,
    cooling_water_usage NUMERIC,
    power_peak_kw NUMERIC,
    energy_cost NUMERIC,
    energy_per_good_piece NUMERIC
);

CREATE TABLE IF NOT EXISTS gold.fact_alerts (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    date_id INTEGER REFERENCES gold.dim_date(date_id),
    machine_id TEXT REFERENCES gold.dim_machine(machine_id),
    alert_type TEXT,
    alert_severity TEXT,
    alert_reason TEXT,
    is_active BOOLEAN
);

CREATE TABLE IF NOT EXISTS gold.fact_supplier_delivery (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    date_id INTEGER REFERENCES gold.dim_date(date_id),
    supplier_id TEXT REFERENCES gold.dim_supplier(supplier_id),
    raw_material_id TEXT REFERENCES gold.dim_raw_material(raw_material_id),
    warehouse_id TEXT REFERENCES gold.dim_warehouse(warehouse_id),
    purchase_order_id TEXT,
    delivery_id TEXT,
    planned_delivery_date TIMESTAMPTZ,
    actual_delivery_date TIMESTAMPTZ,
    supplier_delay_days INTEGER,
    ordered_qty NUMERIC,
    received_qty NUMERIC,
    delivery_status TEXT,
    transport_type TEXT,
    logistics_incident_flag BOOLEAN,
    customs_delay_flag BOOLEAN
);

CREATE TABLE IF NOT EXISTS gold.fact_inventory_snapshot (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    date_id INTEGER REFERENCES gold.dim_date(date_id),
    warehouse_id TEXT REFERENCES gold.dim_warehouse(warehouse_id),
    raw_material_id TEXT REFERENCES gold.dim_raw_material(raw_material_id),
    stock_level NUMERIC,
    safety_stock NUMERIC,
    reorder_point NUMERIC,
    stockout_flag BOOLEAN,
    inventory_turnover NUMERIC,
    reserved_stock_qty NUMERIC,
    available_stock_qty NUMERIC,
    damaged_stock_qty NUMERIC
);

CREATE TABLE IF NOT EXISTS gold.fact_customer_shipment (
    bronze_event_id BIGINT PRIMARY KEY REFERENCES bronze.raw_events(id),
    date_id INTEGER REFERENCES gold.dim_date(date_id),
    customer_id TEXT REFERENCES gold.dim_customer(customer_id),
    warehouse_id TEXT REFERENCES gold.dim_warehouse(warehouse_id),
    shipment_id TEXT,
    shipment_date TIMESTAMPTZ,
    estimated_arrival_date TIMESTAMPTZ,
    actual_arrival_date TIMESTAMPTZ,
    shipping_delay_days INTEGER,
    shipped_qty NUMERIC,
    returned_qty NUMERIC,
    return_reason TEXT,
    logistics_cost NUMERIC
);
