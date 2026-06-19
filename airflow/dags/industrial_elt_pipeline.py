import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg2
from airflow import DAG
from airflow.decorators import task
from airflow.hooks.base import BaseHook


DATALAKE_RAW_DIR = Path(os.getenv("AIRFLOW_VAR_DATALAKE_RAW_DIR", "/opt/airflow/data/datalake/raw"))
POSTGRES_CONN_ID = "industrial_postgres"


def get_postgres_conn():
    airflow_conn = BaseHook.get_connection(POSTGRES_CONN_ID)
    return psycopg2.connect(
        host=airflow_conn.host,
        port=airflow_conn.port or 5432,
        dbname=airflow_conn.schema,
        user=airflow_conn.login,
        password=airflow_conn.password,
    )


def payload_hash(event):
    raw = json.dumps(event, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


with DAG(
    dag_id="industrial_kafka_datalake_elt",
    description="ELT MSPR: datalake brut -> bronze -> silver -> gold dans PostgreSQL",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["mspr", "kafka", "datalake", "elt"],
) as dag:

    @task
    def load_bronze_from_datalake():
        files = sorted(DATALAKE_RAW_DIR.glob("*.jsonl"))
        if not files:
            raise FileNotFoundError(f"Aucun fichier JSONL trouve dans {DATALAKE_RAW_DIR}")

        inserted = 0
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                for path in files:
                    with path.open(encoding="utf-8") as file:
                        for line in file:
                            if not line.strip():
                                continue
                            event = json.loads(line)
                            cur.execute(
                                """
                                INSERT INTO bronze.raw_events (
                                    source_file,
                                    source_system,
                                    ingested_at,
                                    payload,
                                    payload_hash
                                )
                                VALUES (%s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (payload_hash) DO NOTHING
                                """,
                                (
                                    event["source_file"],
                                    event["source_system"],
                                    event.get("datalake_ingested_at"),
                                    json.dumps(event["payload"], ensure_ascii=False),
                                    payload_hash(event),
                                ),
                            )
                            inserted += cur.rowcount
        return inserted

    @task
    def transform_bronze_to_silver():
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO silver.sensor_events (
                        bronze_event_id,
                        event_ts,
                        machine_id,
                        cycle_time_sec,
                        temperature_c,
                        vibration_mms,
                        sound_db,
                        oil_level_pct,
                        coolant_level_pct,
                        hydraulic_pressure_bar,
                        coolant_flow_l_min,
                        heat_index,
                        power_consumption_kw,
                        operational_hours,
                        error_codes_last_30_days,
                        remaining_useful_life_days,
                        predicted_failure_probability,
                        sensor_anomaly_score,
                        ai_override_events,
                        failure_within_7_days,
                        quality_status
                    )
                    SELECT
                        id,
                        NULLIF(payload->>'timestamp', '')::timestamp,
                        NULLIF(payload->>'machine_id', ''),
                        CASE WHEN NULLIF(payload->>'cycle_time_sec', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'cycle_time_sec', '')::numeric BETWEEN 20 AND 120 THEN NULLIF(payload->>'cycle_time_sec', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Temperature_C', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Temperature_C', '')::numeric BETWEEN 0 AND 100 THEN NULLIF(payload->>'Temperature_C', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Vibration_mms', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Vibration_mms', '')::numeric BETWEEN 0 AND 8 THEN NULLIF(payload->>'Vibration_mms', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Sound_dB', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Sound_dB', '')::numeric BETWEEN 40 AND 110 THEN NULLIF(payload->>'Sound_dB', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Oil_Level_pct', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Oil_Level_pct', '')::numeric BETWEEN 0 AND 100 THEN NULLIF(payload->>'Oil_Level_pct', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Coolant_Level_pct', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Coolant_Level_pct', '')::numeric BETWEEN 0 AND 100 THEN NULLIF(payload->>'Coolant_Level_pct', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Hydraulic_Pressure_bar', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Hydraulic_Pressure_bar', '')::numeric BETWEEN 50 AND 200 THEN NULLIF(payload->>'Hydraulic_Pressure_bar', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Coolant_Flow_L_min', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Coolant_Flow_L_min', '')::numeric BETWEEN 0 AND 80 THEN NULLIF(payload->>'Coolant_Flow_L_min', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Heat_Index', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Heat_Index', '')::numeric BETWEEN 0 AND 120 THEN NULLIF(payload->>'Heat_Index', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Power_Consumption_kW', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Power_Consumption_kW', '')::numeric BETWEEN 0 AND 120 THEN NULLIF(payload->>'Power_Consumption_kW', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'Operational_Hours', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN NULLIF(payload->>'Operational_Hours', '')::numeric END,
                        COALESCE(CASE WHEN NULLIF(payload->>'Error_Codes_Last_30_Days', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN NULLIF(payload->>'Error_Codes_Last_30_Days', '')::numeric::integer END, 0),
                        CASE WHEN NULLIF(payload->>'Remaining_Useful_Life_days', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'Remaining_Useful_Life_days', '')::numeric BETWEEN 0 AND 365 THEN NULLIF(payload->>'Remaining_Useful_Life_days', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'predicted_failure_probability', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'predicted_failure_probability', '')::numeric BETWEEN 0 AND 1 THEN NULLIF(payload->>'predicted_failure_probability', '')::numeric END,
                        CASE WHEN NULLIF(payload->>'sensor_anomaly_score', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' AND NULLIF(payload->>'sensor_anomaly_score', '')::numeric BETWEEN 0 AND 1 THEN NULLIF(payload->>'sensor_anomaly_score', '')::numeric END,
                        COALESCE(CASE WHEN NULLIF(payload->>'AI_Override_Events', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN NULLIF(payload->>'AI_Override_Events', '')::numeric::integer END, 0),
                        COALESCE(CASE WHEN NULLIF(payload->>'Failure_Within_7_Days', '') ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN NULLIF(payload->>'Failure_Within_7_Days', '')::numeric::integer END, 0),
                        CASE
                            WHEN payload ? 'Temperature_C'
                             AND payload ? 'Vibration_mms'
                             AND payload ? 'Power_Consumption_kW'
                            THEN 'valid_sensor_event'
                            ELSE 'partial_sensor_event'
                        END
                    FROM bronze.raw_events
                    WHERE source_system = 'scada_capteurs'
                    ON CONFLICT (bronze_event_id) DO NOTHING
                    """
                )
                return cur.rowcount

    @task
    def build_gold_machine_health():
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO gold.machine_health_daily (
                        snapshot_date,
                        machine_id,
                        event_count,
                        avg_temperature_c,
                        avg_vibration_mms,
                        avg_power_consumption_kw,
                        avg_sensor_anomaly_score,
                        failure_alerts,
                        high_risk_events
                    )
                    SELECT
                        event_ts::date,
                        machine_id,
                        COUNT(*)::integer,
                        ROUND(AVG(temperature_c), 2),
                        ROUND(AVG(vibration_mms), 2),
                        ROUND(AVG(power_consumption_kw), 2),
                        ROUND(AVG(sensor_anomaly_score), 3),
                        SUM(CASE WHEN failure_within_7_days = 1 THEN 1 ELSE 0 END)::integer,
                        SUM(
                            CASE
                                WHEN COALESCE(sensor_anomaly_score, 0) >= 0.7
                                  OR COALESCE(predicted_failure_probability, 0) >= 0.7
                                THEN 1 ELSE 0
                            END
                        )::integer
                    FROM silver.sensor_events
                    WHERE event_ts IS NOT NULL
                      AND machine_id IS NOT NULL
                    GROUP BY event_ts::date, machine_id
                    ON CONFLICT (snapshot_date, machine_id) DO UPDATE SET
                        event_count = EXCLUDED.event_count,
                        avg_temperature_c = EXCLUDED.avg_temperature_c,
                        avg_vibration_mms = EXCLUDED.avg_vibration_mms,
                        avg_power_consumption_kw = EXCLUDED.avg_power_consumption_kw,
                        avg_sensor_anomaly_score = EXCLUDED.avg_sensor_anomaly_score,
                        failure_alerts = EXCLUDED.failure_alerts,
                        high_risk_events = EXCLUDED.high_risk_events,
                        generated_at = NOW()
                    """
                )
                return cur.rowcount

    load_bronze_from_datalake() >> transform_bronze_to_silver() >> build_gold_machine_health()
