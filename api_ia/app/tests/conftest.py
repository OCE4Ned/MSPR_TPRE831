from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest

from app.dto.predictions import MachineFeatures, SensorReading
from app.services.model_registry import LoadedModel, ModelNotLoadedError


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
            raise ModelNotLoadedError(f"Model '{key}' not loaded")
        return self._models[key]

    def list(self) -> dict[str, LoadedModel]:
        return dict(self._models)


def _sample_sensors() -> SensorReading:
    return SensorReading(
        machine_id="M-001",
        cycle_time_sec=120.0,
        temperature_c=78.5,
        vibration_mms=3.2,
        sound_db=65.0,
        oil_level_pct=50.0,
        coolant_level_pct=60.0,
        hydraulic_pressure_bar=200.0,
        coolant_flow_l_min=10.0,
        heat_index=30.0,
        power_consumption_kw=5.0,
        operational_hours=1000.0,
        error_codes_last_30_days=2,
        quality_status="OK",
        ai_override_events=1,
    )


@pytest.fixture
def features() -> MachineFeatures:
    """Une lecture machine valide réutilisable dans les tests."""
    return MachineFeatures(
        machine_id="M-001",
        site="lyon",
        timestamp=datetime.now(timezone.utc),
        sensors=_sample_sensors(),
    )


@pytest.fixture
def registry() -> FakeRegistry:
    return FakeRegistry()
