import random
import unittest

from pipeline.machine_stream_simulator import FactoryFlowSimulator, build_tick_events


def machine(machine_id, old_machine_id):
    return {
        "old_machine_id": old_machine_id,
        "machine_id": machine_id,
        "machine_type": "CNC",
        "factory_id": "FR01",
        "machine_generation": "recent",
        "criticality_level": "medium",
        "maintenance_strategy": "preventive",
    }


PARTS = [{
    "product_id": "P001",
    "part_name": "Pièce test",
    "eligible_factory_ids": "FR01",
    "product_family": "Freinage automobile",
}]


class FactoryFlowSimulatorTests(unittest.TestCase):
    def setUp(self):
        random.seed(42)
        self.machines = [machine("MACHINE_1", "M01"), machine("MACHINE_2", "M02")]
        self.simulator = FactoryFlowSimulator(self.machines, PARTS)

    def test_part_keeps_identity_and_moves_to_next_machine(self):
        first_tick, _ = self.simulator.process_tick(1)
        part = first_tick[0][1]
        self.assertEqual(first_tick[0][0]["machine_id"], "MACHINE_1")

        second_tick, _ = self.simulator.process_tick(2)
        part_operations = [item for item in second_tick if item[1].part_instance_id == part.part_instance_id]
        self.assertEqual(part_operations[0][0]["machine_id"], "MACHINE_2")
        self.assertEqual(part_operations[0][1].batch_id, part.batch_id)
        self.assertIn(part, self.simulator.completed_parts)

    def test_machine_health_and_hours_evolve_cumulatively(self):
        state = self.simulator.machine_states["MACHINE_1"]
        initial_health = state.health
        initial_hours = state.operational_hours
        self.simulator.process_tick(1)
        self.assertLess(state.health, initial_health)
        self.assertGreater(state.operational_hours, initial_hours)

    def test_maintenance_restores_health_and_makes_part_wait(self):
        state = self.simulator.machine_states["MACHINE_1"]
        state.health = 34
        processed, maintenance = self.simulator.process_tick(1)
        self.assertFalse(any(item[0]["machine_id"] == "MACHINE_1" for item in processed))
        self.assertEqual(len(maintenance), 1)
        self.assertGreater(state.health, 34)
        self.assertEqual(self.simulator.active_parts[0].operation_index, 0)

    def test_logistics_event_updates_inventory_and_preserves_calculations(self):
        timestamp = "2026-07-01T10:00:00+00:00"
        events = build_tick_events(self.simulator, self.machines, 1, timestamp, 0)
        logistics = next(event["payload"] for event in events if event["source_system"] == "logistique")
        expected_available = max(
            0,
            logistics["stock_level"]
            - logistics["reserved_stock_qty"]
            - logistics["damaged_stock_qty"],
        )
        self.assertAlmostEqual(logistics["available_stock_qty"], expected_available, places=2)
        self.assertEqual(logistics["stockout_flag"], expected_available <= 0)
        self.assertTrue(logistics["purchase_order_id"].startswith("PO-STREAM-"))


if __name__ == "__main__":
    unittest.main()
