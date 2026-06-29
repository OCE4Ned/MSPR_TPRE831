from contextlib import asynccontextmanager
from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.deps import get_registry
from app.dto.predictions import MachineFeatures
from app.main import app
from app.tests.conftest import FakeRegistry, _sample_sensors


@asynccontextmanager
async def _noop_lifespan(_):
    yield


@pytest.fixture
def client(registry: FakeRegistry):
    # On surcharge la dépendance get_registry pour qu'elle renvoie notre fake
    app.dependency_overrides[get_registry] = lambda: registry
    app.dependency_overrides[get_session] = lambda: None
    # On évite que le vrai lifespan tente de charger des modèles
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    app.state.registry = registry
    app.state.ready = True
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.router.lifespan_context = original_lifespan
        app.dependency_overrides.clear()


def _payload(machine_id: str = "M-001") -> dict:
    return MachineFeatures(
        machine_id=machine_id,
        site="lyon",
        timestamp=datetime.now(timezone.utc),
        sensors=_sample_sensors(),
    ).model_dump(mode="json")


def test_predict_state_endpoint_returns_200(client, registry):
    registry.set_model("state_classifier", np.array([[0.1, 0.9]]))

    response = client.post(
        "/api/v1/predictions/state",
        json=_payload(),
        headers={"X-API-Key": "dev-key-change-me"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "at_risk"
    assert body["risk_score"] == pytest.approx(0.9)


def test_predict_state_endpoint_requires_api_key(client, registry):
    registry.set_model("state_classifier", np.array([[0.1, 0.9]]))

    response = client.post("/api/v1/predictions/state", json=_payload())

    assert response.status_code == 401


def test_predict_state_endpoint_rejects_invalid_payload(client):
    response = client.post(
        "/api/v1/predictions/state",
        json={"machine_id": "M-001"},
        headers={"X-API-Key": "dev-key-change-me"},
    )

    assert response.status_code == 422


def test_predict_state_endpoint_returns_503_when_model_missing(client):
    response = client.post(
        "/api/v1/predictions/state",
        json=_payload(),
        headers={"X-API-Key": "dev-key-change-me"},
    )

    assert response.status_code == 503
