# tests/conftest.py
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest

from app.dto.predictions import MachineFeatures, SensorReading
from app.services.model_registry import LoadedModel


@dataclass
class FakeModel:
    """Renvoie une valeur fixe quoi qu'on lui donne en entrée."""
    return_value: Any

    def predict(self, _input):
        return self.return_value


class FakeRegistry:
    """Implémente la même interface que ModelRegistry sans MLflow."""

    def __init__(self):
        self._models: dict[str, LoadedModel] = {}

    def set_model(self, key: str, return_value: Any, version: str = "1") -> None:
        self._models[key] = LoadedModel(
            model=FakeModel(return_value),
            name=f"fake-{key}",
            version=version,
            alias="test",
        )

    def get(self, key: str) -> LoadedModel:
        if key not in self._models:
            raise RuntimeError(f"Model '{key}' not loaded")
        return self._models[key]

    def list(self) -> dict[str, LoadedModel]:
        return dict(self._models)


@pytest.fixture
def features() -> MachineFeatures:
    """Une lecture machine valide réutilisable dans les tests."""
    return MachineFeatures(
        machine_id="M-001",
        site="lyon",
        timestamp=datetime.now(timezone.utc),
        sensors=SensorReading(
            cycle_time_sec=120.0,
            temperature_C=78.5,
            vibration_mms=3.2,
            sound_dB=65.0,
            oil_level_pct=50.0,
            coolant_level_pct=60.0,
            hydraulic_pressure_bar=200.0,
            coolant_flow_L_min=10.0,
            heat_index=30.0,
            power_consumption_kW=5.0,
            operational_hours=1000.0,
            error_codes_last_30_days=2,
            sensor_anomaly_score=0.2,
            ai_override_events=1,
            flag_temperature_high=False,
            flag_vibration_high=False,
            flag_sound_high=False,
            flag_oil_low=False,
            flag_coolant_low=False,
            flag_pressure_low=False,
            flag_coolant_flow_low=False,
            flag_heat_high=False,
            flag_power_high=False,
            flag_error_codes_high=False,
            flag_anomaly_high=False,
            degradation_score=0.5,
            degradation_rate_pct=1.0,
            predicted_failure_probability=0.1,
            remaining_useful_life_days=30.0,
            failure_within_7_days=False,
            maintenance_required_within_45_days=False,
        )
    )


@pytest.fixture
def registry() -> FakeRegistry:
    return FakeRegistry()