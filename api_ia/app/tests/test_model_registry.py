import os

import mlflow
import pytest

from app.services.model_registry import ModelRegistry


def test_model_registry_sets_mlflow_basic_auth_env(monkeypatch):
    captured = {}

    def fake_set_tracking_uri(tracking_uri):
        captured["tracking_uri"] = tracking_uri

    class FakeClient:
        pass

    monkeypatch.delenv("MLFLOW_TRACKING_USERNAME", raising=False)
    monkeypatch.delenv("MLFLOW_TRACKING_PASSWORD", raising=False)
    monkeypatch.setattr(mlflow, "set_tracking_uri", fake_set_tracking_uri)
    monkeypatch.setattr(mlflow, "MlflowClient", lambda: FakeClient())

    ModelRegistry(
        tracking_uri="https://example.test",
        tracking_username="alice",
        tracking_password="secret",
    )

    assert captured["tracking_uri"] == "https://example.test"
    assert os.environ["MLFLOW_TRACKING_USERNAME"] == "alice"
    assert os.environ["MLFLOW_TRACKING_PASSWORD"] == "secret"


def test_model_registry_rejects_partial_mlflow_basic_auth(monkeypatch):
    monkeypatch.setattr(mlflow, "set_tracking_uri", lambda tracking_uri: None)
    monkeypatch.setattr(mlflow, "MlflowClient", lambda: object())

    with pytest.raises(ValueError, match="must be configured together"):
        ModelRegistry(
            tracking_uri="https://example.test",
            tracking_username="alice",
        )