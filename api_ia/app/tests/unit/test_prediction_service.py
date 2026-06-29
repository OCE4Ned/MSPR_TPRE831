from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from app.db.models import PredictionRecord
from app.services.prediction_service import PredictionService


def test_predict_state_returns_at_risk_when_proba_above_threshold(features, registry):
    # RandomForest/XGBoost via pyfunc renvoient les probas en (N, n_classes)
    registry.set_model("state_classifier", np.array([[0.2, 0.8]]))
    service = PredictionService(registry)

    result = service.predict_state(features)

    assert result.machine_id == "M-001"
    assert result.state == "at_risk"
    assert result.risk_score == pytest.approx(0.8)
    assert result.model_version == "1"


def test_predict_state_returns_normal_when_proba_below_threshold(features, registry):
    registry.set_model("state_classifier", np.array([[0.9, 0.1]]))
    service = PredictionService(registry)

    result = service.predict_state(features)

    assert result.state == "normal"
    assert result.risk_score == pytest.approx(0.1)


def test_predict_state_accepts_pyfunc_dataframe_output(features, registry):
    # Le wrapper pyfunc custom renvoie un DataFrame avec colonne risk_score
    registry.set_model(
        "state_classifier",
        pd.DataFrame({"risk_score": [0.65]}),
    )
    service = PredictionService(registry)

    result = service.predict_state(features)

    assert result.state == "at_risk"
    assert result.risk_score == pytest.approx(0.65)


def test_predict_rul_clamps_negative_predictions_to_zero(features, registry):
    # Un régresseur peut très bien sortir une valeur négative
    registry.set_model("rul_regressor", np.array([-12.5]))
    service = PredictionService(registry)

    result = service.predict_rul(features)

    assert result.remaining_useful_life_days == 0.0


def test_detect_anomaly_parses_isolation_forest_native_output(features, registry):
    # IsolationForest brut renvoie -1 (anomalie) ou 1 (normal)
    registry.set_model("anomaly_detector", np.array([-1]))
    service = PredictionService(registry)

    result = service.detect_anomaly(features)

    assert result.is_anomaly is True
    assert result.anomaly_score == -1.0


def test_predict_state_raises_when_model_not_loaded(features, registry):
    # Aucun modèle n'a été enregistré
    service = PredictionService(registry)

    with pytest.raises(RuntimeError, match="state_classifier"):
        service.predict_state(features)


def test_predict_state_batch_vectorized(features, registry):
    # Pour 3 machines, on renvoie 3 lignes de probas
    registry.set_model(
        "state_classifier",
        np.array([[0.9, 0.1], [0.3, 0.7], [0.95, 0.05]]),
    )
    service = PredictionService(registry)
    batch = [features, features.model_copy(update={"machine_id": "M-002"}),
             features.model_copy(update={"machine_id": "M-003"})]

    results = service.predict_state_batch(batch)

    assert [r.machine_id for r in results] == ["M-001", "M-002", "M-003"]
    assert [r.state for r in results] == ["normal", "at_risk", "normal"]


def test_predict_state_persists_record_when_session_present(features, registry):
    registry.set_model("state_classifier", np.array([[0.2, 0.8]]))
    session = MagicMock()
    service = PredictionService(registry, session=session)

    service.predict_state(features)

    assert session.add.call_count == 1
    session.commit.assert_called_once()
    record = session.add.call_args.args[0]
    assert isinstance(record, PredictionRecord)
    assert record.machine_id == "M-001"
    assert record.action == "state"
    assert record.output["risk_score"] == pytest.approx(0.8)


def test_predict_state_batch_persists_one_record_per_item(features, registry):
    registry.set_model(
        "state_classifier",
        np.array([[0.9, 0.1], [0.3, 0.7], [0.95, 0.05]]),
    )
    session = MagicMock()
    service = PredictionService(registry, session=session)
    batch = [features, features.model_copy(update={"machine_id": "M-002"}),
             features.model_copy(update={"machine_id": "M-003"})]

    service.predict_state_batch(batch)

    assert session.add.call_count == 3
    # Batch path commits once, not per-row.
    session.commit.assert_called_once()


def test_predict_state_does_not_break_when_persist_fails(features, registry):
    registry.set_model("state_classifier", np.array([[0.2, 0.8]]))
    session = MagicMock()
    session.commit.side_effect = RuntimeError("db down")
    service = PredictionService(registry, session=session)

    # Prediction must still return successfully even if persistence fails.
    result = service.predict_state(features)

    assert result.state == "at_risk"
    session.rollback.assert_called_once()