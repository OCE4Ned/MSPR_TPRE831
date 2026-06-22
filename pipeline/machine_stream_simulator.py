import csv
import json
import os
import random
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaProducer


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "industrial.raw")
MACHINE_MAPPING_PATH = Path(os.getenv("MACHINE_MAPPING_PATH", "data/processed/business/machine_mapping.csv"))
PARTS_PATH = Path(os.getenv("PARTS_PATH", "data/processed/business/parts.csv"))
SEND_INTERVAL_SECONDS = float(os.getenv("SEND_INTERVAL_SECONDS", "2"))
MAX_EVENTS = int(os.getenv("MAX_EVENTS", "0"))
RANDOM_SEED = os.getenv("RANDOM_SEED")

running = True


def stop(_signum, _frame):
    global running
    running = False


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def choose_product(parts, factory_id):
    eligible_parts = [
        part
        for part in parts
        if factory_id in (part.get("eligible_factory_ids") or "").split("|")
    ]
    return random.choice(eligible_parts or parts)


def clamp(value, minimum, maximum):
    return round(max(minimum, min(maximum, value)), 3)


def bool_text(value):
    return "True" if value else "False"


def base_context(machine, part):
    return {
        "old_machine_id": machine.get("old_machine_id"),
        "machine_id": machine.get("machine_id"),
        "machine_name": machine.get("machine_name"),
        "machine_type": machine.get("machine_type"),
        "factory_id": machine.get("factory_id"),
        "factory_name": machine.get("factory_name"),
        "country": machine.get("country"),
        "production_line_id": machine.get("production_line_id"),
        "production_line_name": machine.get("production_line_name"),
        "product_id": part.get("product_id"),
        "part_name": part.get("part_name"),
        "product_family": part.get("product_family") or machine.get("product_family"),
        "manufacturer": machine.get("manufacturer"),
        "criticality_level": machine.get("criticality_level"),
        "machine_generation": machine.get("machine_generation"),
        "site_maturity_level": machine.get("site_maturity_level"),
        "equipment_level": machine.get("equipment_level"),
        "sensor_reliability": machine.get("sensor_reliability"),
        "data_quality_level": machine.get("data_quality_level"),
        "maintenance_strategy": machine.get("maintenance_strategy"),
        "machine_availability_profile": machine.get("machine_availability_profile"),
        "oee_profile": machine.get("oee_profile"),
        "unplanned_downtime_profile": machine.get("unplanned_downtime_profile"),
        "quality_drift_profile": machine.get("quality_drift_profile"),
        "energy_efficiency_profile": machine.get("energy_efficiency_profile"),
        "systems_maturity": machine.get("systems_maturity"),
    }


def make_scada_payload(timestamp, machine, part):
    critical = machine.get("criticality_level") == "critical"
    older = machine.get("machine_generation") == "older"
    stress = random.random() + (0.2 if critical else 0) + (0.15 if older else 0)

    temperature = clamp(random.gauss(63 + stress * 9, 6), 20, 105)
    vibration = clamp(random.gauss(2.2 + stress * 1.2, 0.6), 0, 9)
    sound = clamp(random.gauss(72 + stress * 8, 5), 40, 115)
    oil = clamp(random.gauss(76 - stress * 13, 8), 0, 100)
    coolant = clamp(random.gauss(73 - stress * 12, 9), 0, 100)
    pressure = clamp(random.gauss(126 - stress * 16, 14), 30, 210)
    coolant_flow = clamp(random.gauss(39 - stress * 7, 6), 0, 85)
    power = clamp(random.gauss(42 + stress * 10, 8), 5, 130)
    heat_index = clamp((temperature * 0.75) + (power * 0.25), 0, 130)
    anomaly = clamp((stress - 0.35) + random.gauss(0, 0.12), 0, 1)
    failure_probability = clamp((anomaly * 0.75) + random.gauss(0.08, 0.08), 0, 1)

    context = base_context(machine, part)
    context.update(
        {
            "timestamp": timestamp,
            "cycle_time_sec": round(random.gauss(45 + stress * 5, 4), 2),
            "Temperature_C": temperature,
            "Vibration_mms": vibration,
            "Sound_dB": sound,
            "Oil_Level_pct": oil,
            "Coolant_Level_pct": coolant,
            "Hydraulic_Pressure_bar": pressure,
            "Coolant_Flow_L_min": coolant_flow,
            "Heat_Index": heat_index,
            "Power_Consumption_kW": power,
            "Operational_Hours": round(random.uniform(500, 9000), 2),
            "Error_Codes_Last_30_Days": int(random.gauss(2 + stress * 4, 2)),
            "sensor_anomaly_score": anomaly,
            "AI_Override_Events": int(random.random() < anomaly * 0.25),
            "flag_temperature_high": int(temperature >= 82),
            "flag_vibration_high": int(vibration >= 5),
            "flag_sound_high": int(sound >= 90),
            "flag_oil_low": int(oil <= 35),
            "flag_coolant_low": int(coolant <= 35),
            "flag_pressure_low": int(pressure <= 80),
            "flag_coolant_flow_low": int(coolant_flow <= 20),
            "flag_heat_high": int(heat_index >= 85),
            "flag_power_high": int(power >= 80),
            "flag_error_codes_high": int(stress >= 1),
            "flag_anomaly_high": int(anomaly >= 0.7),
            "degradation_score": round(anomaly * 100, 2),
            "degradation_rate_pct": round(random.uniform(0, 5) + anomaly * 20, 2),
            "predicted_failure_probability": failure_probability,
            "Remaining_Useful_Life_days": round(max(1, 365 - anomaly * 320 + random.gauss(0, 20)), 1),
            "Failure_Within_7_Days": int(failure_probability >= 0.78),
            "Maintenance_Required_Within_45_Days": int(failure_probability >= 0.55),
        }
    )
    return context


def make_mes_payload(timestamp, machine, part, scada_payload):
    planned_qty = random.randint(850, 1200)
    scrap_rate = clamp(random.gauss(0.025 + scada_payload["sensor_anomaly_score"] * 0.08, 0.015), 0, 0.25)
    actual_qty = int(planned_qty * random.uniform(0.88, 1.05))
    scrap_qty = int(actual_qty * scrap_rate)
    good_qty = max(0, actual_qty - scrap_qty)
    defect = scrap_qty > planned_qty * 0.04

    context = base_context(machine, part)
    context.update(
        {
            "timestamp": timestamp,
            "plant_id": machine.get("factory_id"),
            "batch_id": f"BATCH{random.randint(1000, 9999)}",
            "work_order_id": f"WO{random.randint(1000, 9999)}",
            "actual_production_qty": actual_qty,
            "good_qty": good_qty,
            "scrap_qty": scrap_qty,
            "production_speed": round(random.uniform(18, 35), 2),
            "machine_status": "running" if random.random() > 0.04 else "degraded",
            "downtime_minutes": round(random.uniform(0, 45) * scada_payload["sensor_anomaly_score"], 2),
            "setup_time_minutes": round(random.uniform(10, 45), 2),
            "operator_id": f"OP{random.randint(1, 12):02d}",
            "inspection_id": f"INS{random.randint(10000, 99999)}",
            "dimension_measurement": round(random.gauss(10, 0.25 + scrap_rate), 3),
            "tolerance_min": 9.5,
            "tolerance_max": 10.5,
            "defect_type": "surface_defect" if defect else "no_defect",
            "defect_category": "visual" if defect else "none",
            "defect_severity": "major" if scrap_rate >= 0.08 else "minor",
            "is_conforming": bool_text(not defect),
            "scrap_flag": bool_text(defect),
            "rework_required": bool_text(defect and random.random() > 0.4),
            "quality_score": round(max(0, 100 - scrap_rate * 350), 2),
            "vision_defect_detected": bool_text(defect),
            "operator_validation": bool_text(random.random() > 0.03),
        }
    )
    return context


def make_energy_payload(timestamp, machine, part, scada_payload):
    context = base_context(machine, part)
    context.update(
        {
            "timestamp": timestamp,
            "energy_consumption_kwh": round(scada_payload["Power_Consumption_kW"] * random.uniform(0.65, 1.15), 2),
            "compressed_air_usage": round(random.uniform(10, 35), 2),
            "cooling_water_usage": round(random.uniform(8, 24), 2),
            "power_peak_kw": round(scada_payload["Power_Consumption_kW"] * random.uniform(1.05, 1.55), 2),
            "energy_cost": round(random.uniform(35, 85), 2),
        }
    )
    return context


def make_gmao_payload(timestamp, machine, part, scada_payload, event_number):
    context = base_context(machine, part)
    failure_probability = scada_payload["predicted_failure_probability"]
    context.update(
        {
            "maintenance_event_id": f"MEV_STREAM_{event_number:08d}",
            "timestamp": timestamp,
            "Last_Maintenance_Days_Ago": random.randint(5, 140),
            "Maintenance_History_Count": random.randint(1, 18),
            "Failure_History_Count": random.randint(0, 8),
            "maintenance_type": "corrective" if failure_probability >= 0.75 else "preventive",
            "failure_type": random.choice(["mechanical", "hydraulic", "electrical", "sensor"]),
            "failure_code": random.choice(["F001", "F002", "F003", "F004"]),
            "failure_severity": "critical" if failure_probability >= 0.75 else random.choice(["minor", "major"]),
            "repair_time_minutes": round(random.uniform(20, 180), 2),
            "downtime_minutes": round(random.uniform(15, 240), 2),
            "technician_id": f"TECH{random.randint(1, 8):02d}",
            "spare_part_used": random.choice(["bearing", "valve", "sensor", "belt", "motor"]),
            "maintenance_cost": round(random.uniform(250, 15000), 2),
            "predicted_failure_probability": failure_probability,
            "sensor_anomaly_score": scada_payload["sensor_anomaly_score"],
        }
    )
    return context


def make_event(source_system, row_number, payload):
    return {
        "source_file": "industrial_realtime_stream",
        "source_system": source_system,
        "row_number": row_number,
        "ingestion_mode": "realtime_machine_simulator",
        "payload": payload,
    }


def main():
    if RANDOM_SEED:
        random.seed(RANDOM_SEED)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    machines = read_csv(MACHINE_MAPPING_PATH)
    parts = read_csv(PARTS_PATH)
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )

    sent = 0
    tick = 0
    print(f"Simulation temps reel demarree: {len(machines)} machines -> Kafka topic={TOPIC}")

    try:
        while running and (MAX_EVENTS <= 0 or sent < MAX_EVENTS):
            tick += 1
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

            for machine in machines:
                part = choose_product(parts, machine.get("factory_id"))
                scada_payload = make_scada_payload(timestamp, machine, part)
                events = [
                    make_event("scada_capteurs", tick, scada_payload),
                    make_event("mes", tick, make_mes_payload(timestamp, machine, part, scada_payload)),
                    make_event("energie", tick, make_energy_payload(timestamp, machine, part, scada_payload)),
                ]

                if scada_payload["predicted_failure_probability"] >= 0.65 or random.random() < 0.03:
                    events.append(make_event("gmao", tick, make_gmao_payload(timestamp, machine, part, scada_payload, sent)))

                for event in events:
                    producer.send(TOPIC, key=event["source_system"], value=event)
                    sent += 1
                    if MAX_EVENTS > 0 and sent >= MAX_EVENTS:
                        break

                if MAX_EVENTS > 0 and sent >= MAX_EVENTS:
                    break

            producer.flush()
            print(f"{sent} evenements temps reel envoyes dans Kafka")
            if running and (MAX_EVENTS <= 0 or sent < MAX_EVENTS):
                time.sleep(SEND_INTERVAL_SECONDS)
    finally:
        producer.flush()
        producer.close()
        print(f"Simulation arretee apres {sent} evenements")


if __name__ == "__main__":
    main()
