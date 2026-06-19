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
