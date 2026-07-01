"""Tests unitaires du client IA (app.services.ia_client).

On remplace le transport HTTP par httpx.MockTransport : aucun appel reseau
reel n'est effectue.
"""

import httpx
import pytest

from app.services import ia_client


def _patch_transport(monkeypatch, handler):
    """Force ia_client._client() a utiliser un transport simule."""
    def fake_client():
        return httpx.Client(
            base_url=ia_client.IA_API_BASE_URL,
            headers={"X-API-Key": ia_client.IA_API_KEY},
            transport=httpx.MockTransport(handler),
        )
    monkeypatch.setattr(ia_client, "_client", fake_client)


def test_sensor_fields_complete():
    # Le modele attend 14 champs de capteur.
    assert len(ia_client.SENSOR_FIELDS) == 14
    assert "temperature_c" in ia_client.SENSOR_FIELDS
    assert "ai_override_events" in ia_client.SENSOR_FIELDS


def test_predict_state_batch_sends_key_and_parses(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["key"] = request.headers.get("X-API-Key")
        return httpx.Response(200, json=[
            {"machine_id": "M1", "state": "at_risk", "risk_score": 1.0,
             "model_name": "clf", "model_version": "1"},
        ])

    _patch_transport(monkeypatch, handler)
    out = ia_client.predict_state_batch([{"machine_id": "M1"}])

    assert seen["path"] == "/api/v1/predictions/state/batch"
    assert seen["key"] == ia_client.IA_API_KEY
    assert out[0]["state"] == "at_risk"


def test_predict_state_batch_raises_on_error(monkeypatch):
    _patch_transport(monkeypatch, lambda req: httpx.Response(500, json={}))
    with pytest.raises(httpx.HTTPError):
        ia_client.predict_state_batch([{"machine_id": "M1"}])


def test_predict_rul_many_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "machine_id": "M1", "remaining_useful_life_days": 80.3,
            "model_name": "mecha-rul-regressor", "model_version": "1",
        })

    _patch_transport(monkeypatch, handler)
    out = ia_client.predict_rul_many([{"machine_id": "M1"}, {"machine_id": "M2"}])

    assert len(out) == 2
    assert out[0]["remaining_useful_life_days"] == 80.3
    assert out[0]["model_name"] == "mecha-rul-regressor"


def test_predict_rul_many_tolerates_failure(monkeypatch):
    # 503 systematique (cas reel de l'endpoint anomaly) -> days None, pas d'exception.
    _patch_transport(monkeypatch, lambda req: httpx.Response(503, json={}))
    out = ia_client.predict_rul_many([{"machine_id": "M1"}, {"machine_id": "M2"}])

    assert [r["machine_id"] for r in out] == ["M1", "M2"]
    assert all(r["remaining_useful_life_days"] is None for r in out)
