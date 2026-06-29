from __future__ import annotations


import numpy as np
import pandas as pd

from app.ml import features as feat
from app.dto.predictions import (
    AnomalyResponse,
    MachineFeatures,
    MachineSequence,
    RulResponse,
    StateResponse,
)
from app.services.model_registry import LoadedModel


class TabularStatePredictor:
    """RandomForestClassifier, XGBClassifier"""

    def __init__(self, loaded: LoadedModel, threshold: float = 0.5):
        self._loaded = loaded
        self.threshold = threshold

    def predict(self, features: MachineFeatures) -> StateResponse:
        df = feat.features_to_dataframe(features)
        raw = self._loaded.model.predict(df)
        risk = self._risk_score(raw)
        return StateResponse(
            machine_id=features.machine_id,
            state="at_risk" if risk >= self.threshold else "normal",
            risk_score=risk,
            model_name=self._loaded.name,
            model_version=self._loaded.version,
        )

    @staticmethod
    def _risk_score(raw) -> float:
        if isinstance(raw, pd.DataFrame) and "risk_score" in raw.columns:
            return float(raw["risk_score"].iloc[0])
        arr = np.asarray(raw)
        if arr.ndim == 2 and arr.shape[1] == 2:
            return float(arr[0, 1])
        return float(arr.ravel()[0])
    
    def predict_batch(self, items: list[MachineFeatures]) -> list[StateResponse]:
        df = feat.features_batch_to_dataframe(items)
        raw = self._loaded.model.predict(df)
        risks = self._risk_scores(raw)  # ndarray (N,)
        return [
            StateResponse(
                machine_id=f.machine_id,
                state="at_risk" if r >= self.threshold else "normal",
                risk_score=float(r),
                model_name=self._loaded.name,
                model_version=self._loaded.version,
            )
            for f, r in zip(items, risks)
        ]

    @staticmethod
    def _risk_scores(raw) -> np.ndarray:
        if isinstance(raw, pd.DataFrame) and "risk_score" in raw.columns:
            return raw["risk_score"].to_numpy()
        arr = np.asarray(raw)
        if arr.ndim == 2 and arr.shape[1] == 2:
            return arr[:, 1]
        return arr.ravel()


class TabularRulPredictor:
    """RandomForestRegressor, XGBRegressor"""

    def __init__(self, loaded: LoadedModel):
        self._loaded = loaded

    def predict(self, features: MachineFeatures) -> RulResponse:
        df = feat.features_to_dataframe(features)
        raw = self._loaded.model.predict(df)
        rul = self._extract_rul(raw)
        return RulResponse(
            machine_id=features.machine_id,
            remaining_useful_life_days=rul,
            model_name=self._loaded.name,
            model_version=self._loaded.version,
        )

    @staticmethod
    def _extract_rul(raw) -> float:
        if isinstance(raw, pd.DataFrame) and "predicted_rul_days" in raw.columns:
            return max(0.0, float(raw["predicted_rul_days"].iloc[0]))
        return max(0.0, float(np.asarray(raw).ravel()[0]))


class IsolationForestAnomalyDetector:
    """IsolationForest : .predict() = -1/1, .score_samples() = anomaly score."""

    def __init__(self, loaded: LoadedModel):
        self._loaded = loaded

    def predict(self, features: MachineFeatures) -> AnomalyResponse:
        df = feat.features_to_dataframe(features)
        raw = self._loaded.model.predict(df)
        if isinstance(raw, pd.DataFrame):
            score = float(raw["anomaly_score"].iloc[0])
            is_anomaly = bool(raw["is_anomaly"].iloc[0])
        else:
            arr = np.asarray(raw).ravel()
            score = float(arr[0])
            is_anomaly = score < 0
        return AnomalyResponse(
            machine_id=features.machine_id,
            is_anomaly=is_anomaly,
            anomaly_score=score,
            model_name=self._loaded.name,
            model_version=self._loaded.version,
        )


class SequenceRulPredictor:
    """LSTM Keras ou PyTorch : prend une séquence (1, T, F)."""

    def __init__(self, loaded: LoadedModel):
        self._loaded = loaded

    def predict(self, sequence: MachineSequence) -> RulResponse:
        arr = feat.sequence_to_array(sequence)
        raw = self._loaded.model.predict(arr)
        rul = float(np.asarray(raw).ravel()[0])
        return RulResponse(
            machine_id=sequence.machine_id,
            remaining_useful_life_days=max(0.0, rul),
            model_name=self._loaded.name,
            model_version=self._loaded.version,
        )