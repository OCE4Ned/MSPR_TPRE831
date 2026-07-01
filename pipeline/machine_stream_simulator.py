import csv
import json
import os
import random
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "industrial.raw")
MACHINE_MAPPING_PATH = Path(os.getenv("MACHINE_MAPPING_PATH", "data/processed/business/machine_mapping.csv"))
PARTS_PATH = Path(os.getenv("PARTS_PATH", "data/processed/business/parts.csv"))
SEND_INTERVAL_SECONDS = float(os.getenv("SEND_INTERVAL_SECONDS", "2"))
MAX_EVENTS = int(os.getenv("MAX_EVENTS", "0"))
RANDOM_SEED = os.getenv("RANDOM_SEED")
WEAR_ACCELERATION = float(os.getenv("WEAR_ACCELERATION", "1"))
MAINTENANCE_THRESHOLD = float(os.getenv("MAINTENANCE_THRESHOLD", "35"))

SUPPLIER_PROFILES = [
    {"supplier_id": "SUP001", "supplier_name": "Aciers Rhône", "raw_material_id": "RM001", "raw_material_name": "Acier allié 42CrMo4", "reliability": 0.92, "transport_type": "camion"},
    {"supplier_id": "SUP002", "supplier_name": "Alu Iberica", "raw_material_id": "RM002", "raw_material_name": "Aluminium 7075", "reliability": 0.86, "transport_type": "rail"},
    {"supplier_id": "SUP003", "supplier_name": "Composites Europe", "raw_material_id": "RM003", "raw_material_name": "Composite carbone", "reliability": 0.78, "transport_type": "bateau"},
    {"supplier_id": "SUP004", "supplier_name": "Fluides Techniques", "raw_material_id": "RM004", "raw_material_name": "Fluide hydraulique", "reliability": 0.95, "transport_type": "camion"},
]

running = True


def stop(_signum, _frame):
    global running
    running = False


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def clamp(value, minimum, maximum):
    return round(max(minimum, min(maximum, value)), 3)


def bool_text(value):
    return "True" if value else "False"


def machine_operation_rank(machine):
    """Use an explicit route sequence, or fall back to the legacy M01..M08 order."""
    explicit_sequence = machine.get("route_sequence")
    if explicit_sequence not in (None, ""):
        return int(explicit_sequence)
    old_id = machine.get("old_machine_id") or ""
    digits = "".join(character for character in old_id if character.isdigit())
    return int(digits) if digits else 999


def product_difficulty(part):
    family = (part.get("product_family") or "").lower()
    if "aéronaut" in family or "aeronaut" in family or "turbomachine" in family:
        return 1.35
    if "transmission" in family or "moteur" in family:
        return 1.15
    return 1.0


def initial_health(machine):
    generation = machine.get("machine_generation")
    return {"recent": 94.0, "mid_life": 84.0, "older": 72.0}.get(generation, 88.0)


def initial_hours(machine):
    generation = machine.get("machine_generation")
    base = {"recent": 1200.0, "mid_life": 4800.0, "older": 8200.0}.get(generation, 3000.0)
    # A stable per-machine offset avoids identical counters without random jumps.
    offset = sum(ord(char) for char in machine.get("machine_id", "")) % 500
    return base + offset


@dataclass
class MachineState:
    health: float
    operational_hours: float
    cycles_since_maintenance: int = 0
    maintenance_count: int = 0
    last_maintenance_tick: int = 0
    error_count: int = 0


@dataclass
class PartFlow:
    part_instance_id: str
    batch_id: str
    work_order_id: str
    part: dict
    factory_id: str
    route: list
    created_tick: int
    operation_index: int = 0
    operation_history: list = field(default_factory=list)

    @property
    def complete(self):
        return self.operation_index >= len(self.route)

    @property
    def next_machine(self):
        return None if self.complete else self.route[self.operation_index]


class FactoryFlowSimulator:
    """Stateful production flow shared by Kafka execution and unit tests."""

    def __init__(self, machines, parts):
        self.parts = parts
        self.routes = {}
        for machine in machines:
            self.routes.setdefault(machine.get("factory_id"), []).append(machine)
        for route in self.routes.values():
            route.sort(key=lambda machine: (machine_operation_rank(machine), machine.get("machine_id", "")))

        self.machine_states = {
            machine["machine_id"]: MachineState(initial_health(machine), initial_hours(machine))
            for machine in machines
        }
        self.active_parts = []
        self.completed_parts = []
        self.part_sequence = 0
        self.logistics_sequence = 0
        self.inventory = {
            (factory_id, supplier["raw_material_id"]): 900.0
            for factory_id in self.routes
            for supplier in SUPPLIER_PROFILES
        }

    def choose_product(self, factory_id):
        eligible = [
            part for part in self.parts
            if factory_id in (part.get("eligible_factory_ids") or "").split("|")
        ]
        return random.choice(eligible or self.parts)

    def create_part(self, factory_id, tick):
        self.part_sequence += 1
        part = self.choose_product(factory_id)
        instance_id = f"PART-{factory_id}-{self.part_sequence:08d}"
        flow = PartFlow(
            part_instance_id=instance_id,
            batch_id=f"BATCH-{factory_id}-{(self.part_sequence - 1) // 20 + 1:06d}",
            work_order_id=f"WO-{factory_id}-{(self.part_sequence - 1) // 100 + 1:05d}",
            part=part,
            factory_id=factory_id,
            route=self.routes[factory_id],
            created_tick=tick,
        )
        self.active_parts.append(flow)
        return flow

    def perform_maintenance(self, machine, tick):
        state = self.machine_states[machine["machine_id"]]
        health_before = state.health
        strategy = machine.get("maintenance_strategy")
        maintenance_type = "preventive" if strategy == "preventive" else "corrective"
        recovery = 38 if maintenance_type == "preventive" else 52
        state.health = min(92.0, state.health + recovery)
        state.cycles_since_maintenance = 0
        state.error_count = max(0, state.error_count - 4)
        state.maintenance_count += 1
        state.last_maintenance_tick = tick
        return maintenance_type, health_before

    def process_tick(self, tick):
        """Create one part per factory and advance every eligible part by one step."""
        for factory_id in sorted(self.routes):
            self.create_part(factory_id, tick)

        occupied_machines = set()
        processed = []
        maintenance = []

        # Oldest pieces have priority, which creates a real FIFO queue after downtime.
        for flow in sorted(self.active_parts, key=lambda item: (item.created_tick, item.part_instance_id)):
            machine = flow.next_machine
            if machine is None:
                continue
            machine_id = machine["machine_id"]
            if machine_id in occupied_machines:
                continue
            occupied_machines.add(machine_id)
            state = self.machine_states[machine_id]

            if state.health <= MAINTENANCE_THRESHOLD:
                maintenance_type, health_before = self.perform_maintenance(machine, tick)
                maintenance.append((machine, flow, maintenance_type, health_before))
                continue

            difficulty = product_difficulty(flow.part)
            criticality_factor = 1.18 if machine.get("criticality_level") == "critical" else 1.0
            cycle_hours = max(0.005, random.gauss(48, 3) / 3600)
            wear = (0.035 + cycle_hours * 1.8) * difficulty * criticality_factor * WEAR_ACCELERATION
            health_before = state.health
            state.health = max(0.0, state.health - wear)
            state.operational_hours += cycle_hours
            state.cycles_since_maintenance += 1
            if state.health < 60 and random.random() < (60 - state.health) / 800:
                state.error_count += 1

            operation = {
                "operation_sequence": flow.operation_index + 1,
                "operation_name": machine.get("machine_type"),
                "machine_id": machine_id,
                "tick": tick,
                "health_before_pct": round(health_before, 3),
                "health_after_pct": round(state.health, 3),
            }
            flow.operation_history.append(operation)
            flow.operation_index += 1
            processed.append((machine, flow, operation))

        completed = [flow for flow in self.active_parts if flow.complete]
        self.completed_parts.extend(completed)
        self.active_parts = [flow for flow in self.active_parts if not flow.complete]
        return processed, maintenance


def base_context(machine, flow=None):
    part = flow.part if flow else {}
    context = {
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
    }
    if flow:
        context.update({
            "part_instance_id": flow.part_instance_id,
            "batch_id": flow.batch_id,
            "work_order_id": flow.work_order_id,
            "operation_sequence": flow.operation_index,
            "total_operations": len(flow.route),
        })
    return context


def make_scada_payload(timestamp, machine, state, flow=None):
    degradation = clamp(1 - state.health / 100, 0, 1)
    temperature = clamp(random.gauss(57 + degradation * 38, 2.5), 20, 105)
    vibration = clamp(random.gauss(1.2 + degradation * 5.5, 0.25), 0, 9)
    sound = clamp(random.gauss(66 + degradation * 28, 2.5), 40, 115)
    oil = clamp(random.gauss(94 - degradation * 55, 3), 0, 100)
    coolant = clamp(random.gauss(91 - degradation * 50, 3.5), 0, 100)
    pressure = clamp(random.gauss(145 - degradation * 65, 5), 30, 210)
    coolant_flow = clamp(random.gauss(39 - degradation * 22, 2), 0, 85)
    power = clamp(random.gauss(36 + degradation * 42, 3), 5, 130)
    heat_index = clamp(temperature * 0.75 + power * 0.25, 0, 130)
    anomaly = clamp(degradation + random.gauss(0, 0.025), 0, 1)
    failure_probability = clamp((degradation ** 2) * 0.85 + state.error_count * 0.025, 0, 1)
    rul_days = clamp(state.health * 3.65 - state.error_count * 4, 1, 365)

    context = base_context(machine, flow)
    context.update({
        "timestamp": timestamp,
        "machine_health_pct": round(state.health, 3),
        "cycles_since_maintenance": state.cycles_since_maintenance,
        "maintenance_count": state.maintenance_count,
        "cycle_time_sec": round(random.gauss(44 + degradation * 12, 1.8), 2),
        "Temperature_C": temperature,
        "Vibration_mms": vibration,
        "Sound_dB": sound,
        "Oil_Level_pct": oil,
        "Coolant_Level_pct": coolant,
        "Hydraulic_Pressure_bar": pressure,
        "Coolant_Flow_L_min": coolant_flow,
        "Heat_Index": heat_index,
        "Power_Consumption_kW": power,
        "Operational_Hours": round(state.operational_hours, 3),
        "Error_Codes_Last_30_Days": state.error_count,
        "sensor_anomaly_score": anomaly,
        "AI_Override_Events": int(failure_probability >= 0.7),
        "flag_temperature_high": int(temperature >= 82),
        "flag_vibration_high": int(vibration >= 5),
        "flag_sound_high": int(sound >= 90),
        "flag_oil_low": int(oil <= 35),
        "flag_coolant_low": int(coolant <= 35),
        "flag_pressure_low": int(pressure <= 80),
        "flag_coolant_flow_low": int(coolant_flow <= 20),
        "flag_heat_high": int(heat_index >= 85),
        "flag_power_high": int(power >= 80),
        "flag_error_codes_high": int(state.error_count >= 4),
        "flag_anomaly_high": int(anomaly >= 0.7),
        "degradation_score": round(degradation * 15.2, 2),
        "degradation_rate_pct": round(degradation * 100, 2),
        "predicted_failure_probability": failure_probability,
        "Remaining_Useful_Life_days": rul_days,
        "Failure_Within_7_Days": int(rul_days <= 7 or failure_probability >= 0.78),
        "Maintenance_Required_Within_45_Days": int(rul_days <= 45 or failure_probability >= 0.55),
    })
    return context


def make_mes_payload(timestamp, machine, flow, operation, scada_payload):
    degradation = 1 - scada_payload["machine_health_pct"] / 100
    scrap_probability = clamp(0.01 + degradation * 0.18, 0, 0.3)
    defect = random.random() < scrap_probability
    context = base_context(machine, flow)
    context.update({
        "timestamp": timestamp,
        "plant_id": machine.get("factory_id"),
        "operation_sequence": operation["operation_sequence"],
        "operation_name": operation["operation_name"],
        "operation_status": "completed",
        "actual_production_qty": 1,
        "good_qty": 0 if defect else 1,
        "scrap_qty": 1 if defect else 0,
        "production_speed": round(3600 / scada_payload["cycle_time_sec"], 2),
        "machine_status": "degraded" if degradation >= 0.55 else "running",
        "downtime_minutes": 0,
        "setup_time_minutes": 0,
        "operator_id": f"OP{(sum(ord(c) for c in machine['machine_id']) % 12) + 1:02d}",
        "inspection_id": f"INS-{flow.part_instance_id}-{operation['operation_sequence']:02d}",
        "dimension_measurement": round(random.gauss(10, 0.08 + degradation * 0.3), 3),
        "tolerance_min": 9.5,
        "tolerance_max": 10.5,
        "defect_type": "surface_defect" if defect else "no_defect",
        "defect_category": "visual" if defect else "none",
        "defect_severity": "major" if defect and degradation >= 0.6 else "minor",
        "is_conforming": bool_text(not defect),
        "scrap_flag": bool_text(defect),
        "rework_required": bool_text(defect and random.random() > 0.4),
        "quality_score": round(max(0, 100 - degradation * 22 - (30 if defect else 0)), 2),
        "vision_defect_detected": bool_text(defect),
        "operator_validation": bool_text(not defect),
        "machine_health_before_pct": operation["health_before_pct"],
        "machine_health_after_pct": operation["health_after_pct"],
    })
    return context


def make_energy_payload(timestamp, machine, state, scada_payload, flow=None):
    context = base_context(machine, flow)
    active_factor = 1.0 if flow else 0.18
    consumption = scada_payload["Power_Consumption_kW"] * SEND_INTERVAL_SECONDS / 3600 * active_factor
    context.update({
        "timestamp": timestamp,
        "energy_consumption_kwh": round(consumption, 4),
        "compressed_air_usage": round(random.uniform(10, 35) * active_factor, 2),
        "cooling_water_usage": round(random.uniform(8, 24) * active_factor, 2),
        "power_peak_kw": round(scada_payload["Power_Consumption_kW"] * random.uniform(1.05, 1.2), 2),
        "energy_cost": round(consumption * 0.22, 4),
        "machine_health_pct": round(state.health, 3),
    })
    return context


def make_gmao_payload(timestamp, machine, flow, state, maintenance_type, health_before, event_number):
    context = base_context(machine, flow)
    context.update({
        "maintenance_event_id": f"MEV_STREAM_{event_number:08d}",
        "timestamp": timestamp,
        "Last_Maintenance_Days_Ago": 0,
        "Maintenance_History_Count": state.maintenance_count,
        "Failure_History_Count": state.error_count,
        "maintenance_type": maintenance_type,
        "failure_type": "wear",
        "failure_code": "WEAR_THRESHOLD",
        "failure_severity": "major" if maintenance_type == "corrective" else "minor",
        "repair_time_minutes": 45 if maintenance_type == "preventive" else 120,
        "downtime_minutes": 45 if maintenance_type == "preventive" else 120,
        "technician_id": f"TECH{state.maintenance_count % 8 + 1:02d}",
        "spare_part_used": "wear_kit",
        "maintenance_cost": 1200 if maintenance_type == "preventive" else 5500,
        "health_before_maintenance_pct": round(health_before, 3),
        "health_after_maintenance_pct": round(state.health, 3),
        "predicted_failure_probability": round((1 - health_before / 100) ** 2, 3),
        "sensor_anomaly_score": round(1 - health_before / 100, 3),
    })
    return context


def make_logistics_payload(timestamp, simulator, factory_id, tick, processed_count):
    """Create a coherent supplier delivery, inventory snapshot and customer shipment."""
    simulator.logistics_sequence += 1
    sequence = simulator.logistics_sequence
    supplier = SUPPLIER_PROFILES[(tick + sequence) % len(SUPPLIER_PROFILES)]
    material_id = supplier["raw_material_id"]
    inventory_key = (factory_id, material_id)
    stock_before = simulator.inventory[inventory_key]
    safety_stock = 180
    reorder_point = 350
    ordered_qty = 600 if stock_before <= reorder_point else 0
    missing_delivery = ordered_qty > 0 and random.random() > supplier["reliability"]
    received_qty = 0 if missing_delivery else ordered_qty
    supplier_delay = random.choice([-1, 0, 0, 0, 1, 2, 5]) if ordered_qty else 0

    event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    planned_delivery = event_time - timedelta(days=supplier_delay)
    actual_delivery = None if missing_delivery or ordered_qty == 0 else event_time
    production_consumption = processed_count * random.uniform(2.5, 5.0)
    shipped_qty = random.randint(0, 25)
    damaged_qty = random.randint(0, 2) if random.random() < 0.04 else 0
    stock_level = max(0, stock_before + received_qty - production_consumption - shipped_qty)
    reserved_qty = min(stock_level, processed_count * 8)
    available_qty = max(0, stock_level - reserved_qty - damaged_qty)
    simulator.inventory[inventory_key] = stock_level

    shipping_delay = random.choice([-1, 0, 0, 0, 1, 2])
    shipment_date = event_time
    estimated_arrival = shipment_date + timedelta(days=3)
    actual_arrival = estimated_arrival + timedelta(days=shipping_delay) if shipped_qty else None
    delivery_status = "missing" if missing_delivery else ("delayed" if supplier_delay > 0 else "on_time")
    customer_number = (sequence % 4) + 1

    return {
        "timestamp": timestamp,
        "plant_id": factory_id,
        "supplier_id": supplier["supplier_id"],
        "supplier_name": supplier["supplier_name"],
        "raw_material_id": material_id,
        "raw_material_name": supplier["raw_material_name"],
        "purchase_order_id": f"PO-STREAM-{sequence:08d}",
        "delivery_id": f"DEL-STREAM-{sequence:08d}",
        "planned_delivery_date": planned_delivery.isoformat(),
        "actual_delivery_date": actual_delivery.isoformat() if actual_delivery else None,
        "supplier_delay_days": supplier_delay if actual_delivery else None,
        "received_qty": round(received_qty, 2),
        "ordered_qty": ordered_qty,
        "delivery_status": delivery_status,
        "transport_type": supplier["transport_type"],
        "logistics_incident_flag": supplier_delay >= 5 or missing_delivery,
        "customs_delay_flag": supplier["transport_type"] == "bateau" and supplier_delay >= 3,
        "warehouse_id": f"WH_{factory_id}",
        "stock_level": round(stock_level, 2),
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "stockout_flag": available_qty <= 0,
        "inventory_turnover": round(4 + shipped_qty / max(stock_level, 1) * 365, 2),
        "reserved_stock_qty": round(reserved_qty, 2),
        "available_stock_qty": round(available_qty, 2),
        "damaged_stock_qty": damaged_qty,
        "shipment_id": f"SHP-STREAM-{sequence:08d}",
        "customer_id": f"CUS{customer_number:03d}",
        "customer_region": ["France", "Europe du Sud", "Europe du Nord", "International"][customer_number - 1],
        "shipment_date": shipment_date.isoformat() if shipped_qty else None,
        "estimated_arrival_date": estimated_arrival.isoformat() if shipped_qty else None,
        "actual_arrival_date": actual_arrival.isoformat() if actual_arrival else None,
        "shipping_delay_days": shipping_delay if actual_arrival else None,
        "shipped_qty": shipped_qty,
        "returned_qty": 0,
        "return_reason": "unknown",
        "logistics_cost": round(80 + shipped_qty * 0.75, 2) if shipped_qty else 0,
    }


def make_event(source_system, row_number, payload):
    return {
        "source_file": "industrial_realtime_stream",
        "source_system": source_system,
        "row_number": row_number,
        "ingestion_mode": "realtime_machine_simulator",
        "payload": payload,
    }


def build_tick_events(simulator, machines, tick, timestamp, sent):
    processed, maintenance = simulator.process_tick(tick)
    processed_by_machine = {machine["machine_id"]: (flow, operation) for machine, flow, operation in processed}
    events = []

    for machine in machines:
        state = simulator.machine_states[machine["machine_id"]]
        flow_operation = processed_by_machine.get(machine["machine_id"])
        flow = flow_operation[0] if flow_operation else None
        scada = make_scada_payload(timestamp, machine, state, flow)
        events.append(make_event("scada_capteurs", tick, scada))
        events.append(make_event("energie", tick, make_energy_payload(timestamp, machine, state, scada, flow)))
        if flow_operation:
            events.append(make_event("mes", tick, make_mes_payload(timestamp, machine, flow, flow_operation[1], scada)))

    for index, (machine, flow, maintenance_type, health_before) in enumerate(maintenance, start=1):
        state = simulator.machine_states[machine["machine_id"]]
        payload = make_gmao_payload(timestamp, machine, flow, state, maintenance_type, health_before, sent + index)
        events.append(make_event("gmao", tick, payload))

    for factory_id in sorted(simulator.routes):
        processed_count = sum(1 for machine, _, _ in processed if machine.get("factory_id") == factory_id)
        logistics = make_logistics_payload(timestamp, simulator, factory_id, tick, processed_count)
        events.append(make_event("logistique", tick, logistics))
    return events


def main():
    from kafka import KafkaProducer

    if RANDOM_SEED:
        random.seed(RANDOM_SEED)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    machines = read_csv(MACHINE_MAPPING_PATH)
    parts = read_csv(PARTS_PATH)
    simulator = FactoryFlowSimulator(machines, parts)
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )

    sent = 0
    tick = 0
    print(f"Simulation avec flux métier démarrée: {len(machines)} machines -> Kafka topic={TOPIC}")
    try:
        while running and (MAX_EVENTS <= 0 or sent < MAX_EVENTS):
            tick += 1
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            events = build_tick_events(simulator, machines, tick, timestamp, sent)
            for event in events:
                producer.send(TOPIC, key=event["source_system"], value=event)
                sent += 1
                if MAX_EVENTS > 0 and sent >= MAX_EVENTS:
                    break
            producer.flush()
            print(
                f"tick={tick} événements={sent} pièces_en_cours={len(simulator.active_parts)} "
                f"pièces_terminées={len(simulator.completed_parts)}"
            )
            if running and (MAX_EVENTS <= 0 or sent < MAX_EVENTS):
                time.sleep(SEND_INTERVAL_SECONDS)
    finally:
        producer.flush()
        producer.close()
        print(f"Simulation arrêtée après {sent} événements")


if __name__ == "__main__":
    main()
