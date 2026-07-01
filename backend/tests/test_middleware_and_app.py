"""Tests du middleware d'origine et des routes ne touchant pas la base."""

from fastapi.testclient import TestClient

from app.main import app
from app.middleware.origin import get_allowed_origins

client = TestClient(app)


# --- get_allowed_origins ----------------------------------------------------

def test_allowed_origins_default(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    origins = get_allowed_origins()
    assert "http://localhost:5173" in origins


def test_allowed_origins_from_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.com, http://b.com ")
    assert get_allowed_origins() == ["http://a.com", "http://b.com"]


# --- OriginCheckMiddleware (via l'app) --------------------------------------

def test_root_without_origin_ok():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Ceci est le backend de la solution!"}


def test_root_with_allowed_origin_ok():
    resp = client.get("/", headers={"origin": "http://localhost:5173"})
    assert resp.status_code == 200


def test_root_with_unknown_origin_blocked():
    resp = client.get("/", headers={"origin": "http://attaquant.example"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Origine non autorisee"


# --- Routes stub (non implementees) -----------------------------------------

def test_predict_failure_not_implemented():
    resp = client.post("/predict/failure", json={"machine_id": "M1"})
    assert resp.status_code == 501


def test_metrics_endpoint_exposed():
    resp = client.get("/metrics")
    assert resp.status_code == 200
