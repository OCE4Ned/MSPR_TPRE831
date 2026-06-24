import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.deps import get_registry
from app.dto.predictions import MachineFeatures
from app.main import app
from app.tests.conftest import FakeRegistry


@pytest.fixture
def client(registry: FakeRegistry):
    # On surcharge la dépendance get_registry pour qu'elle renvoie notre fake
    app.dependency_overrides[get_registry] = lambda: registry
    # On évite que le vrai lifespan tente de charger des modèles
    app.router.lifespan_context = None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_predict_state_endpoint_returns_200(client, registry):
    registry.set_model("state_classifier", np.array([[0.1, 0.9]]))
    payload = MachineFeatures(
        timestamp="2026-06-20T10:00:00Z",
        machine_id="M-001",
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
    ).model_dump()

    response = client.post(
        "/api/v1/predictions/state",
        json=payload,
        headers={"X-API-Key": "dev-key-change-me"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "at_risk"
    assert body["risk_score"] == pytest.approx(0.9)


def test_predict_state_endpoint_requires_api_key(client, registry):
    registry.set_model("state_classifier", np.array([[0.1, 0.9]]))
    payload = MachineFeatures(
        timestamp="2026-06-20T10:00:00Z",
        machine_id="M-001",
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
    ).model_dump()

    response = client.post("/api/v1/predictions/state", json=payload)

    assert response.status_code == 401


def test_predict_state_endpoint_rejects_invalid_payload(client):
    response = client.post(
        "/api/v1/predictions/state",
        json={"machine_id": "M-001"},
        headers={"X-API-Key": "dev-key-change-me"},
    )

    assert response.status_code == 422