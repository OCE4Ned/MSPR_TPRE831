from fastapi import APIRouter, Body, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.deps import get_registry, verify_api_key
from app.dto.predictions import (
    AnomalyResponse,
    MachineFeatures,
    MachineSequence,
    RulResponse,
    StateResponse,
)
from app.services.model_registry import ModelRegistry
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/predictions", tags=["predictions"])


def get_service(
    registry: ModelRegistry = Depends(get_registry),
    session: Session | None = Depends(get_session),
) -> PredictionService:
    return PredictionService(registry, session)


@router.post("/state", response_model=StateResponse, dependencies=[Depends(verify_api_key)])
def predict_state(
    features: MachineFeatures,
    service: PredictionService = Depends(get_service),
):
    return service.predict_state(features)


@router.post("/rul", response_model=RulResponse, dependencies=[Depends(verify_api_key)])
def predict_rul(
    features: MachineFeatures,
    service: PredictionService = Depends(get_service),
):
    return service.predict_rul(features)


@router.post("/rul/sequence", response_model=RulResponse, dependencies=[Depends(verify_api_key)])
def predict_rul_sequence(
    sequence: MachineSequence,
    service: PredictionService = Depends(get_service),
):
    return service.predict_rul_sequence(sequence)


@router.post("/anomaly", response_model=AnomalyResponse, dependencies=[Depends(verify_api_key)])
def detect_anomaly(
    features: MachineFeatures,
    service: PredictionService = Depends(get_service),
):
    return service.detect_anomaly(features)


@router.post(
    "/state/batch",
    response_model=list[StateResponse],
    dependencies=[Depends(verify_api_key)],
)
def predict_state_batch(
    items: list[MachineFeatures] = Body(..., min_length=1, max_length=500),
    service: PredictionService = Depends(get_service),
):
    return service.predict_state_batch(items)
