import logging
import time
from contextlib import contextmanager
from typing import Iterator

from pydantic import BaseModel
from sqlmodel import Session

from app.config import get_settings
from app.db.models import PredictionRecord
from app.dto.predictions import (
    AnomalyResponse,
    MachineFeatures,
    MachineSequence,
    RulResponse,
    StateResponse,
)
from app.services.model_registry import LoadedModel, ModelRegistry
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
    def __init__(self, registry: ModelRegistry, session: Session | None = None):
        self._registry = registry
        self._session = session

    def predict_state(self, features: MachineFeatures) -> StateResponse:
        with _track("state", features.machine_id):
            loaded = self._registry.get("state_classifier")
            response = TabularStatePredictor(loaded, settings.risk_threshold).predict(features)
            self._record("state", loaded, features, response)
            return response

    def predict_rul(self, features: MachineFeatures) -> RulResponse:
        with _track("rul", features.machine_id):
            loaded = self._registry.get("rul_regressor")
            response = TabularRulPredictor(loaded).predict(features)
            self._record("rul", loaded, features, response)
            return response

    def predict_rul_sequence(self, sequence: MachineSequence) -> RulResponse:
        with _track("rul_seq", sequence.machine_id):
            loaded = self._registry.get("rul_lstm")
            response = SequenceRulPredictor(loaded).predict(sequence)
            self._record("rul_seq", loaded, sequence, response)
            return response

    def detect_anomaly(self, features: MachineFeatures) -> AnomalyResponse:
        with _track("anomaly", features.machine_id):
            loaded = self._registry.get("anomaly_detector")
            response = IsolationForestAnomalyDetector(loaded).predict(features)
            self._record("anomaly", loaded, features, response)
            return response

    def predict_state_batch(self, items: list[MachineFeatures]) -> list[StateResponse]:
        start = time.perf_counter()
        loaded = self._registry.get("state_classifier")
        results = TabularStatePredictor(loaded, settings.risk_threshold).predict_batch(items)
        for features, response in zip(items, results):
            self._record("state", loaded, features, response, flush=False)
        self._flush()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "prediction_batch_ok action=state n=%d elapsed_ms=%.2f", len(items), elapsed_ms
        )
        return results

    def _record(
        self,
        action: str,
        loaded: LoadedModel,
        request: BaseModel,
        response: BaseModel,
        flush: bool = True,
    ) -> None:
        if self._session is None:
            return
        site = getattr(request, "site", None)
        try:
            self._session.add(
                PredictionRecord(
                    machine_id=request.machine_id,
                    site=site,
                    action=action,
                    model_name=loaded.name,
                    model_version=loaded.version,
                    model_alias=loaded.alias,
                    input=request.model_dump(mode="json"),
                    output=response.model_dump(mode="json"),
                )
            )
            if flush:
                self._session.commit()
        except Exception:
            # Persistence is best-effort: never break a successful inference.
            logger.exception(
                "prediction_persist_failed action=%s machine_id=%s",
                action, request.machine_id,
            )
            self._session.rollback()

    def _flush(self) -> None:
        if self._session is None:
            return
        try:
            self._session.commit()
        except Exception:
            logger.exception("prediction_persist_batch_failed")
            self._session.rollback()
