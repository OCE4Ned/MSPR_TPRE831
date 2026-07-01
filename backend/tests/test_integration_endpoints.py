"""Tests d'integration des endpoints qui lisent la base `industrial_dw`.

Tout le module est ignore (skip) si la base n'est pas joignable, afin que la
suite reste verte hors environnement Docker. Les appels au modele IA sont
simules pour ne pas dependre du reseau.
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app
from app.services import ia_client

try:
    with engine.connect() as _conn:
        _conn.execute(text("SELECT 1"))
    DB_UP = True
except Exception:  # noqa: BLE001
    DB_UP = False

pytestmark = pytest.mark.skipif(not DB_UP, reason="Base industrial_dw indisponible")

client = TestClient(app)


@pytest.fixture
def stub_ia(monkeypatch):
    """Remplace les appels IA par des reponses canoniques (aucun reseau)."""
    monkeypatch.setattr(ia_client, "predict_state_batch", lambda feats: [
        {"machine_id": f["machine_id"], "state": "normal", "risk_score": 0.0,
         "model_name": "mecha-failure-7d-classifier", "model_version": "1"}
        for f in feats
    ])
    monkeypatch.setattr(ia_client, "predict_rul_many", lambda feats: [
        {"machine_id": f["machine_id"], "remaining_useful_life_days": 100.0,
         "model_name": "mecha-rul-regressor", "model_version": "1"}
        for f in feats
    ])


def test_sites_returns_fr01():
    resp = client.get("/analytics/sites")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert "FR01" in ids


def test_site_analytics_shape(stub_ia):
    resp = client.get("/analytics/site/FR01")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("factory", "kpis", "trsSeries", "lines", "riskMachines",
                "maintenancePlan", "alerts", "iaIndicators"):
        assert key in data
    assert data["factory"]["id"] == "FR01"
    assert len(data["lines"]) >= 1
    assert data["iaOnline"] is True
    # IA en ligne -> machines a risque enrichies (etat + RUL) et plan trie.
    assert "state" in data["riskMachines"][0]
    assert "rulDays" in data["riskMachines"][0]
    if len(data["maintenancePlan"]) >= 2:
        ruls = [m["rulDays"] for m in data["maintenancePlan"]]
        assert ruls == sorted(ruls)


def test_site_analytics_unknown_site_404(stub_ia):
    resp = client.get("/analytics/site/INCONNU")
    assert resp.status_code == 404


def test_site_analytics_ia_fallback_when_model_down(monkeypatch):
    def boom(_):
        raise httpx.ConnectError("IA injoignable")

    monkeypatch.setattr(ia_client, "predict_state_batch", boom)
    resp = client.get("/analytics/site/FR01")
    assert resp.status_code == 200
    assert resp.json()["iaOnline"] is False


def test_group_analytics_shape():
    resp = client.get("/analytics/group")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("kpis", "trsBySite", "scrapBySite", "energyBySite", "alerts", "siteCount"):
        assert key in data
    assert data["siteCount"] >= 1
    # chaque barre de comparaison porte un label, une valeur et un statut
    for bar in data["trsBySite"]:
        assert {"label", "value", "status"} <= set(bar)


def test_dimensions_plants():
    resp = client.get("/dimensions/plants")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_facts_production_filtered():
    resp = client.get("/facts/production", params={"machine_id": "FOU_FR_001"})
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    if rows:
        assert rows[0]["machine_id"] == "FOU_FR_001"
