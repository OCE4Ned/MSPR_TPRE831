import logging
import time
from contextlib import contextmanager
from typing import Iterator
from app.config import get_settings

from app.dto.predictions import (
    AnomalyResponse,
    MachineFeatures,
    MachineSequence,
    RulResponse,
    StateResponse,
)
from app.services.model_registry import ModelRegistry
from app.services.predictors_service import (
    IsolationForestAnomalyDetector,
    SequenceRulPredictor,
    TabularRulPredictor,
    TabularStatePredictor,
)

logger = logging.getLogger(__name__)
settings = get_settings()

@contextmanager
def _track(action: str, machine_id: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    except Exception:
        logger.exception(
            "prediction_failed action=%s machine_id=%s", action, machine_id
        )
        raise
    else:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "prediction_ok action=%s machine_id=%s elapsed_ms=%.2f",
            action, machine_id, elapsed_ms,
        )


class PredictionService:
    def __init__(self, registry: ModelRegistry):
        self._registry = registry

    def predict_state(self, features: MachineFeatures) -> StateResponse:
        with _track("state", features.machine_id):
            loaded = self._registry.get("state_classifier")
            return TabularStatePredictor(loaded, settings.risk_threshold).predict(features)

    def predict_rul(self, features: MachineFeatures) -> RulResponse:
        with _track("rul", features.machine_id):
            loaded = self._registry.get("rul_regressor")
            return TabularRulPredictor(loaded).predict(features)

    def predict_rul_sequence(self, sequence: MachineSequence) -> RulResponse:
        with _track("rul_seq", sequence.machine_id):
            loaded = self._registry.get("rul_lstm")
            return SequenceRulPredictor(loaded).predict(sequence)

    def detect_anomaly(self, features: MachineFeatures) -> AnomalyResponse:
        with _track("anomaly", features.machine_id):
            loaded = self._registry.get("anomaly_detector")
            return IsolationForestAnomalyDetector(loaded).predict(features)
        
    def predict_state_batch(self, items: list[MachineFeatures]) -> list[StateResponse]:
        start = time.perf_counter()
        loaded = self._registry.get("state_classifier")
        results = TabularStatePredictor(loaded).predict_batch(items)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "prediction_batch_ok action=state n=%d elapsed_ms=%.2f", len(items), elapsed_ms
        )
        return results