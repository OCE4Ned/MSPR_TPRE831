import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from airflow import DAG
from airflow.decorators import task
from airflow.hooks.base import BaseHook


DATALAKE_RAW_DIR = Path(os.getenv("AIRFLOW_VAR_DATALAKE_RAW_DIR", "/opt/airflow/data/datalake/raw"))
POSTGRES_CONN_ID = os.getenv("AIRFLOW_VAR_POSTGRES_CONN_ID", "industrial_dw")


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


def clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def as_number(value):
    value = clean_text(value)
    if value is None or not re.match(r"^-?[0-9]+(\.[0-9]+)?$", value):
        return None
    return float(value)


def as_int(value):
    value = as_number(value)
    return None if value is None else int(round(value))


def as_bool(value):
    value = clean_text(value)
    if value is None:
        return None
    return value.lower() in {"1", "true", "t", "yes", "y", "oui"}


def as_datetime(value):
    value = clean_text(value)
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def make_date_id(value):
    event_dt = as_datetime(value)
    if event_dt is None:
        return None, None
    event_date = event_dt.date()
    return int(event_date.strftime("%Y%m%d")), event_date


def shift_from_payload(payload):
    shift = clean_text(payload.get("shift"))
    if shift:
        shift = shift.lower()
        if shift in {"matin", "morning"}:
            return "SHIFT_MATIN", "matin", "06:00", "14:00"
        if shift in {"apres-midi", "après-midi", "afternoon"}:
            return "SHIFT_APRES_MIDI", "apres-midi", "14:00", "22:00"
        if shift in {"nuit", "night"}:
            return "SHIFT_NUIT", "nuit", "22:00", "06:00"
        return f"SHIFT_{shift.upper().replace(' ', '_')}", shift, "00:00", "23:59"

    event_dt = as_datetime(payload.get("timestamp"))
    hour = event_dt.hour if event_dt else 0
    if 6 <= hour < 14:
        return "SHIFT_MATIN", "matin", "06:00", "14:00"
    if 14 <= hour < 22:
        return "SHIFT_APRES_MIDI", "apres-midi", "14:00", "22:00"
    return "SHIFT_NUIT", "nuit", "22:00", "06:00"


def defect_id(payload):
    defect_type = clean_text(payload.get("defect_type")) or "no_defect"
    defect_category = clean_text(payload.get("defect_category")) or "none"
    defect_severity = clean_text(payload.get("defect_severity")) or "minor"
    raw_id = f"{defect_type}_{defect_category}_{defect_severity}".lower()
    return re.sub(r"[^a-z0-9]+", "_", raw_id).strip("_"), defect_type, defect_category, defect_severity


def rate(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return round(numerator / denominator, 4)


def upsert_dimension_context(cur, payload):
    date_id, event_date = make_date_id(payload.get("timestamp"))
    if date_id and event_date:
        cur.execute(
            """
            INSERT INTO gold.dim_date (date_id, date, year, month, day, week)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date_id) DO NOTHING
            """,
            (date_id, event_date, event_date.year, event_date.month, event_date.day, event_date.isocalendar().week),
        )

    plant_id = clean_text(payload.get("factory_id")) or clean_text(payload.get("plant_id"))
    if plant_id:
        cur.execute(
            """
            INSERT INTO gold.dim_plant (plant_id, plant_name, country)
            VALUES (%s, %s, %s)
            ON CONFLICT (plant_id) DO UPDATE SET
                plant_name = COALESCE(EXCLUDED.plant_name, gold.dim_plant.plant_name),
                country = COALESCE(EXCLUDED.country, gold.dim_plant.country)
            """,
            (plant_id, clean_text(payload.get("factory_name")), clean_text(payload.get("country"))),
        )

    line_id = clean_text(payload.get("production_line_id"))
    if line_id:
        cur.execute(
            """
            INSERT INTO gold.dim_line (production_line_id, plant_id, line_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (production_line_id) DO UPDATE SET
                plant_id = COALESCE(EXCLUDED.plant_id, gold.dim_line.plant_id),
                line_name = COALESCE(EXCLUDED.line_name, gold.dim_line.line_name)
            """,
            (line_id, plant_id, clean_text(payload.get("production_line_name"))),
        )

    shift_id, shift_name, start_hour, end_hour = shift_from_payload(payload)
    cur.execute(
        """
        INSERT INTO gold.dim_shift (shift_id, shift_name, start_hour, end_hour)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (shift_id) DO UPDATE SET
            shift_name = EXCLUDED.shift_name,
            start_hour = EXCLUDED.start_hour,
            end_hour = EXCLUDED.end_hour
        """,
        (shift_id, shift_name, start_hour, end_hour),
    )

    product_id = clean_text(payload.get("product_id"))
    if product_id:
        cur.execute(
            """
            INSERT INTO gold.dim_product (product_id, product_name, product_family)
            VALUES (%s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                product_name = COALESCE(EXCLUDED.product_name, gold.dim_product.product_name),
                product_family = COALESCE(EXCLUDED.product_family, gold.dim_product.product_family)
            """,
            (product_id, clean_text(payload.get("part_name")), clean_text(payload.get("product_family"))),
        )

    machine_id = clean_text(payload.get("machine_id"))
    if machine_id:
        if line_id:
            cur.execute(
                """
                INSERT INTO gold.dim_line (production_line_id, plant_id, line_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (production_line_id) DO NOTHING
                """,
                (line_id, plant_id, clean_text(payload.get("production_line_name"))),
            )
        cur.execute(
            """
            INSERT INTO gold.dim_machine (machine_id, production_line_id, machine_type, installation_year)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (machine_id) DO UPDATE SET
                production_line_id = COALESCE(EXCLUDED.production_line_id, gold.dim_machine.production_line_id),
                machine_type = COALESCE(EXCLUDED.machine_type, gold.dim_machine.machine_type),
                installation_year = COALESCE(EXCLUDED.installation_year, gold.dim_machine.installation_year)
            """,
            (
                machine_id,
                line_id,
                clean_text(payload.get("machine_type")),
                as_int(payload.get("Installation_Year")) or as_int(payload.get("installation_year")),
            ),
        )

    defect_key, defect_type, defect_category, defect_severity = defect_id(payload)
    cur.execute(
        """
        INSERT INTO gold.dim_defect (defect_id, defect_type, defect_category, defect_severity)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (defect_id) DO NOTHING
        """,
        (defect_key, defect_type, defect_category, defect_severity),
    )

    return {
        "date_id": date_id,
        "plant_id": plant_id,
        "line_id": line_id,
        "shift_id": shift_id,
        "product_id": product_id,
        "machine_id": machine_id,
        "defect_id": defect_key,
    }


with DAG(
    dag_id="industrial_kafka_datalake_elt",
    description="ELT MSPR: datalake brut -> bronze -> silver -> gold dans PostgreSQL",
    start_date=datetime(2026, 1, 1),
    schedule="0 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["mspr", "kafka", "datalake", "elt"],
) as dag:

    @task
    def load_bronze_from_datalake():
        files = sorted(DATALAKE_RAW_DIR.glob("*.jsonl"))
        if not files:
            raise FileNotFoundError(f"Aucun fichier JSONL trouve dans {DATALAKE_RAW_DIR}")

        # Insertion par lots (execute_values) : ~200 requetes au lieu de ~1M
        # -> supprime les allers-retours reseau ligne par ligne.
        insert_sql = (
            "INSERT INTO bronze.raw_events "
            "(source_file, source_system, ingested_at, payload, payload_hash) "
            "VALUES %s ON CONFLICT (payload_hash) DO NOTHING"
        )
        template = "(%s, %s, %s, %s::jsonb, %s)"
        batch_size = 5000

        inserted = 0
        batch = []
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:

                def flush():
                    nonlocal inserted
                    if not batch:
                        return
                    # page_size = taille du lot -> 1 requete/flush -> rowcount exact
                    execute_values(cur, insert_sql, batch, template=template, page_size=batch_size)
                    inserted += cur.rowcount
                    batch.clear()

                for path in files:
                    with path.open(encoding="utf-8") as file:
                        for line in file:
                            if not line.strip():
                                continue
                            event = json.loads(line)
                            batch.append((
                                event["source_file"],
                                event["source_system"],
                                event.get("datalake_ingested_at"),
                                json.dumps(event["payload"], ensure_ascii=False),
                                payload_hash(event),
                            ))
                            if len(batch) >= batch_size:
                                flush()
                flush()
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

    @task
    def build_gold_star_schema():
        # Generateurs d'expressions SQL reproduisant les helpers Python
        # (as_number / as_int / clean_text / as_bool) de maniere ensembliste.
        def _num(field):
            return (
                f"CASE WHEN btrim(payload->>'{field}') ~ '^-?[0-9]+(\\.[0-9]+)?$' "
                f"THEN (payload->>'{field}')::numeric END"
            )

        def _int(field):
            return f"round({_num(field)})::int"

        def _txt(field):
            return f"NULLIF(btrim(payload->>'{field}'), '')"

        def _bool(field):
            return (
                f"CASE WHEN {_txt(field)} IS NULL THEN NULL "
                f"ELSE lower(btrim(payload->>'{field}')) IN ('1','true','t','yes','y','oui') END"
            )

        inserted = {
            "fact_production": 0,
            "fact_quality": 0,
            "fact_maintenance": 0,
            "fact_energy": 0,
            "fact_alerts": 0,
        }

        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                # 1) Staging temporaire : derive toutes les cles dimensionnelles
                #    en une seule passe sur bronze (au lieu d'une boucle Python).
                cur.execute(
                    """
                    CREATE TEMP TABLE _stg ON COMMIT DROP AS
                    WITH base AS (
                        SELECT
                            id AS bronze_event_id,
                            source_system,
                            source_file,
                            payload,
                            (right(source_file, 13) = '_business.csv'
                             OR source_file = 'industrial_realtime_stream') AS is_biz,
                            CASE WHEN payload->>'timestamp' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
                                 THEN NULLIF(btrim(payload->>'timestamp'), '')::timestamp END AS ts,
                            lower(NULLIF(btrim(payload->>'shift'), '')) AS shift_txt,
                            COALESCE(NULLIF(btrim(payload->>'factory_id'), ''),
                                     NULLIF(btrim(payload->>'plant_id'), '')) AS plant_id,
                            NULLIF(btrim(payload->>'production_line_id'), '') AS line_id,
                            NULLIF(btrim(payload->>'product_id'), '') AS product_id,
                            NULLIF(btrim(payload->>'machine_id'), '') AS machine_id,
                            COALESCE(NULLIF(btrim(payload->>'defect_type'), ''), 'no_defect') AS defect_type,
                            COALESCE(NULLIF(btrim(payload->>'defect_category'), ''), 'none') AS defect_category,
                            COALESCE(NULLIF(btrim(payload->>'defect_severity'), ''), 'minor') AS defect_severity
                        FROM bronze.raw_events
                        WHERE source_system IN (
                            'mes', 'gmao', 'energie', 'scada_capteurs', 'erp',
                            'machine_mapping', 'factories', 'production_lines', 'parts'
                        )
                    ),
                    derived AS (
                        SELECT
                            base.*,
                            CASE WHEN ts IS NOT NULL THEN to_char(ts, 'YYYYMMDD')::int END AS date_id,
                            CASE
                                WHEN shift_txt IN ('matin', 'morning') THEN 'SHIFT_MATIN'
                                WHEN shift_txt IN ('apres-midi', 'après-midi', 'afternoon') THEN 'SHIFT_APRES_MIDI'
                                WHEN shift_txt IN ('nuit', 'night') THEN 'SHIFT_NUIT'
                                WHEN shift_txt IS NOT NULL THEN 'SHIFT_' || upper(replace(shift_txt, ' ', '_'))
                                WHEN extract(hour FROM ts) >= 6 AND extract(hour FROM ts) < 14 THEN 'SHIFT_MATIN'
                                WHEN extract(hour FROM ts) >= 14 AND extract(hour FROM ts) < 22 THEN 'SHIFT_APRES_MIDI'
                                ELSE 'SHIFT_NUIT'
                            END AS shift_id,
                            btrim(regexp_replace(
                                lower(defect_type || '_' || defect_category || '_' || defect_severity),
                                '[^a-z0-9]+', '_', 'g'), '_') AS defect_id
                        FROM base
                    )
                    SELECT
                        derived.*,
                        CASE shift_id
                            WHEN 'SHIFT_MATIN' THEN 'matin'
                            WHEN 'SHIFT_APRES_MIDI' THEN 'apres-midi'
                            WHEN 'SHIFT_NUIT' THEN 'nuit'
                            ELSE shift_txt
                        END AS shift_name,
                        CASE shift_id
                            WHEN 'SHIFT_MATIN' THEN '06:00'
                            WHEN 'SHIFT_APRES_MIDI' THEN '14:00'
                            WHEN 'SHIFT_NUIT' THEN '22:00'
                            ELSE '00:00'
                        END AS start_hour,
                        CASE shift_id
                            WHEN 'SHIFT_MATIN' THEN '14:00'
                            WHEN 'SHIFT_APRES_MIDI' THEN '22:00'
                            WHEN 'SHIFT_NUIT' THEN '06:00'
                            ELSE '23:59'
                        END AS end_hour
                    FROM derived
                    """
                )

                # 2) Dimensions (ensemblistes, dans l'ordre des contraintes FK)
                cur.execute(
                    """
                    INSERT INTO gold.dim_date (date_id, date, year, month, day, week)
                    SELECT date_id, max(ts::date), max(extract(year FROM ts))::int,
                           max(extract(month FROM ts))::int, max(extract(day FROM ts))::int,
                           max(extract(week FROM ts))::int
                    FROM _stg WHERE date_id IS NOT NULL GROUP BY date_id
                    ON CONFLICT (date_id) DO NOTHING
                    """
                )
                cur.execute(
                    """
                    INSERT INTO gold.dim_plant (plant_id, plant_name, country)
                    SELECT plant_id,
                           max(NULLIF(btrim(payload->>'factory_name'), '')),
                           max(NULLIF(btrim(payload->>'country'), ''))
                    FROM _stg WHERE plant_id IS NOT NULL GROUP BY plant_id
                    ON CONFLICT (plant_id) DO UPDATE SET
                        plant_name = COALESCE(EXCLUDED.plant_name, gold.dim_plant.plant_name),
                        country = COALESCE(EXCLUDED.country, gold.dim_plant.country)
                    """
                )
                cur.execute(
                    """
                    INSERT INTO gold.dim_line (production_line_id, plant_id, line_name)
                    SELECT line_id, max(plant_id),
                           max(NULLIF(btrim(payload->>'production_line_name'), ''))
                    FROM _stg WHERE line_id IS NOT NULL GROUP BY line_id
                    ON CONFLICT (production_line_id) DO UPDATE SET
                        plant_id = COALESCE(EXCLUDED.plant_id, gold.dim_line.plant_id),
                        line_name = COALESCE(EXCLUDED.line_name, gold.dim_line.line_name)
                    """
                )
                cur.execute(
                    """
                    INSERT INTO gold.dim_shift (shift_id, shift_name, start_hour, end_hour)
                    SELECT shift_id, max(shift_name), max(start_hour), max(end_hour)
                    FROM _stg GROUP BY shift_id
                    ON CONFLICT (shift_id) DO UPDATE SET
                        shift_name = EXCLUDED.shift_name,
                        start_hour = EXCLUDED.start_hour,
                        end_hour = EXCLUDED.end_hour
                    """
                )
                cur.execute(
                    """
                    INSERT INTO gold.dim_product (product_id, product_name, product_family)
                    SELECT product_id,
                           max(NULLIF(btrim(payload->>'part_name'), '')),
                           max(NULLIF(btrim(payload->>'product_family'), ''))
                    FROM _stg WHERE product_id IS NOT NULL GROUP BY product_id
                    ON CONFLICT (product_id) DO UPDATE SET
                        product_name = COALESCE(EXCLUDED.product_name, gold.dim_product.product_name),
                        product_family = COALESCE(EXCLUDED.product_family, gold.dim_product.product_family)
                    """
                )
                cur.execute(
                    """
                    INSERT INTO gold.dim_machine (machine_id, production_line_id, machine_type, installation_year)
                    SELECT machine_id, max(line_id),
                           max(NULLIF(btrim(payload->>'machine_type'), '')),
                           max(COALESCE(
                               CASE WHEN btrim(payload->>'Installation_Year') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                                    THEN round((payload->>'Installation_Year')::numeric)::int END,
                               CASE WHEN btrim(payload->>'installation_year') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                                    THEN round((payload->>'installation_year')::numeric)::int END
                           ))
                    FROM _stg WHERE machine_id IS NOT NULL GROUP BY machine_id
                    ON CONFLICT (machine_id) DO UPDATE SET
                        production_line_id = COALESCE(EXCLUDED.production_line_id, gold.dim_machine.production_line_id),
                        machine_type = COALESCE(EXCLUDED.machine_type, gold.dim_machine.machine_type),
                        installation_year = COALESCE(EXCLUDED.installation_year, gold.dim_machine.installation_year)
                    """
                )
                cur.execute(
                    """
                    INSERT INTO gold.dim_defect (defect_id, defect_type, defect_category, defect_severity)
                    SELECT defect_id, max(defect_type), max(defect_category), max(defect_severity)
                    FROM _stg GROUP BY defect_id
                    ON CONFLICT (defect_id) DO NOTHING
                    """
                )

                # 3) Faits : uniquement les evenements business / temps reel
                cur.execute(
                    f"""
                    INSERT INTO gold.fact_production (
                        bronze_event_id, date_id, plant_id, production_line_id, machine_id,
                        product_id, shift_id, planned_production_qty, actual_production_qty,
                        good_qty, scrap_qty, cycle_time_sec, target_cycle_time_sec,
                        production_speed, downtime_minutes, setup_time_minutes,
                        availability_rate, performance_rate, quality_rate, trs, scrap_rate
                    )
                    SELECT
                        bronze_event_id, date_id, plant_id, line_id, machine_id,
                        product_id, shift_id, planned, actual, good, scrap, cyc, target_cyc,
                        speed, downtime, setup, availability, performance, quality,
                        CASE WHEN quality IS NOT NULL AND performance IS NOT NULL
                             THEN round(availability * quality * performance, 4) END AS trs,
                        CASE WHEN scrap IS NOT NULL AND actual IS NOT NULL AND actual <> 0
                             THEN round(scrap::numeric / actual, 4) END AS scrap_rate
                    FROM (
                        SELECT
                            bronze_event_id, date_id, plant_id, line_id, machine_id, product_id, shift_id,
                            {_int('planned_production_qty')} AS planned,
                            {_int('actual_production_qty')} AS actual,
                            {_int('good_qty')} AS good,
                            {_int('scrap_qty')} AS scrap,
                            {_num('cycle_time_sec')} AS cyc,
                            {_num('target_cycle_time_sec')} AS target_cyc,
                            {_num('production_speed')} AS speed,
                            COALESCE({_num('downtime_minutes')}, 0) AS downtime,
                            COALESCE({_num('setup_time_minutes')}, 0) AS setup
                        FROM _stg WHERE source_system = 'mes' AND is_biz
                    ) base,
                    LATERAL (SELECT
                        round(greatest(480 - downtime - setup, 0) / 480.0, 4) AS availability,
                        CASE WHEN good IS NOT NULL AND actual IS NOT NULL AND actual <> 0
                             THEN round(good::numeric / actual, 4) END AS quality,
                        CASE WHEN speed IS NOT NULL THEN round(speed / 100.0, 4) END AS performance
                    ) calc
                    ON CONFLICT (bronze_event_id) DO UPDATE SET
                        actual_production_qty = EXCLUDED.actual_production_qty,
                        good_qty = EXCLUDED.good_qty,
                        scrap_qty = EXCLUDED.scrap_qty,
                        availability_rate = EXCLUDED.availability_rate,
                        performance_rate = EXCLUDED.performance_rate,
                        quality_rate = EXCLUDED.quality_rate,
                        trs = EXCLUDED.trs,
                        scrap_rate = EXCLUDED.scrap_rate
                    """
                )
                inserted["fact_production"] = cur.rowcount

                cur.execute(
                    f"""
                    INSERT INTO gold.fact_quality (
                        bronze_event_id, date_id, machine_id, product_id, defect_id,
                        dimension_measurement, tolerance_min, tolerance_max,
                        is_conforming, scrap_flag, rework_required, quality_score
                    )
                    SELECT bronze_event_id, date_id, machine_id, product_id, defect_id,
                        {_num('dimension_measurement')}, {_num('tolerance_min')}, {_num('tolerance_max')},
                        {_bool('is_conforming')}, {_bool('scrap_flag')}, {_bool('rework_required')},
                        {_num('quality_score')}
                    FROM _stg WHERE source_system = 'mes' AND is_biz
                    ON CONFLICT (bronze_event_id) DO UPDATE SET
                        dimension_measurement = EXCLUDED.dimension_measurement,
                        tolerance_min = EXCLUDED.tolerance_min,
                        tolerance_max = EXCLUDED.tolerance_max,
                        is_conforming = EXCLUDED.is_conforming,
                        scrap_flag = EXCLUDED.scrap_flag,
                        rework_required = EXCLUDED.rework_required,
                        quality_score = EXCLUDED.quality_score
                    """
                )
                inserted["fact_quality"] = cur.rowcount

                cur.execute(
                    f"""
                    INSERT INTO gold.fact_maintenance (
                        bronze_event_id, date_id, machine_id, maintenance_event_id,
                        maintenance_type, failure_type, failure_code, failure_severity,
                        repair_time_minutes, downtime_minutes, maintenance_cost,
                        predicted_failure_probability, sensor_anomaly_score
                    )
                    SELECT bronze_event_id, date_id, machine_id,
                        {_txt('maintenance_event_id')}, {_txt('maintenance_type')}, {_txt('failure_type')},
                        {_txt('failure_code')}, {_txt('failure_severity')},
                        {_num('repair_time_minutes')}, {_num('downtime_minutes')}, {_num('maintenance_cost')},
                        {_num('predicted_failure_probability')}, {_num('sensor_anomaly_score')}
                    FROM _stg WHERE source_system = 'gmao' AND is_biz
                    ON CONFLICT (bronze_event_id) DO UPDATE SET
                        maintenance_type = EXCLUDED.maintenance_type,
                        failure_type = EXCLUDED.failure_type,
                        failure_code = EXCLUDED.failure_code,
                        failure_severity = EXCLUDED.failure_severity,
                        repair_time_minutes = EXCLUDED.repair_time_minutes,
                        downtime_minutes = EXCLUDED.downtime_minutes,
                        maintenance_cost = EXCLUDED.maintenance_cost
                    """
                )
                inserted["fact_maintenance"] = cur.rowcount

                cur.execute(
                    f"""
                    INSERT INTO gold.fact_energy (
                        bronze_event_id, date_id, machine_id, energy_consumption_kwh,
                        compressed_air_usage, cooling_water_usage, power_peak_kw,
                        energy_cost, energy_per_good_piece
                    )
                    SELECT bronze_event_id, date_id, machine_id,
                        {_num('energy_consumption_kwh')}, {_num('compressed_air_usage')},
                        {_num('cooling_water_usage')}, {_num('power_peak_kw')}, {_num('energy_cost')},
                        NULL::numeric
                    FROM _stg WHERE source_system = 'energie' AND is_biz
                    ON CONFLICT (bronze_event_id) DO UPDATE SET
                        energy_consumption_kwh = EXCLUDED.energy_consumption_kwh,
                        compressed_air_usage = EXCLUDED.compressed_air_usage,
                        cooling_water_usage = EXCLUDED.cooling_water_usage,
                        power_peak_kw = EXCLUDED.power_peak_kw,
                        energy_cost = EXCLUDED.energy_cost,
                        energy_per_good_piece = EXCLUDED.energy_per_good_piece
                    """
                )
                inserted["fact_energy"] = cur.rowcount

                cur.execute(
                    """
                    INSERT INTO gold.fact_alerts (
                        bronze_event_id, date_id, machine_id, alert_type,
                        alert_severity, alert_reason, is_active
                    )
                    SELECT bronze_event_id, date_id, machine_id, 'sensor_health',
                        CASE WHEN COALESCE(pfp, 0) >= 0.7 THEN 'critical' ELSE 'warning' END,
                        COALESCE(active_flags, 'predicted_failure_probability_high'), TRUE
                    FROM (
                        SELECT bronze_event_id, date_id, machine_id,
                            (SELECT string_agg(replace(k, 'flag_', ''), ',' ORDER BY k)
                               FROM jsonb_each_text(payload) AS j(k, v)
                               WHERE k LIKE 'flag\\_%' ESCAPE '\\'
                                 AND lower(btrim(v)) IN ('1','true','t','yes','y','oui')) AS active_flags,
                            CASE WHEN btrim(payload->>'predicted_failure_probability') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                                 THEN (payload->>'predicted_failure_probability')::numeric END AS pfp
                        FROM _stg WHERE source_system = 'scada_capteurs' AND is_biz
                    ) a
                    WHERE active_flags IS NOT NULL OR COALESCE(pfp, 0) >= 0.7
                    ON CONFLICT (bronze_event_id) DO UPDATE SET
                        alert_type = EXCLUDED.alert_type,
                        alert_severity = EXCLUDED.alert_severity,
                        alert_reason = EXCLUDED.alert_reason,
                        is_active = EXCLUDED.is_active
                    """
                )
                inserted["fact_alerts"] = cur.rowcount

                cur.execute(
                    """
                    UPDATE gold.fact_energy energy
                    SET energy_per_good_piece = ROUND(energy.energy_consumption_kwh / production.good_qty, 4)
                    FROM gold.fact_production production
                    WHERE energy.date_id = production.date_id
                      AND energy.machine_id = production.machine_id
                      AND production.good_qty IS NOT NULL
                      AND production.good_qty > 0
                      AND energy.energy_consumption_kwh IS NOT NULL
                    """
                )

        return inserted

    bronze = load_bronze_from_datalake()
    silver = transform_bronze_to_silver()
    health = build_gold_machine_health()
    star = build_gold_star_schema()

    bronze >> [silver, star]
    silver >> health
