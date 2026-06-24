"""Routes liees aux predictions (maintenance predictive)."""

from fastapi import APIRouter, HTTPException

from app.dto.ai_pred import FailurePredictionRequest, FailurePredictionResponse

router = APIRouter(prefix="/predict", tags=["predictions"])


@router.post("/failure", response_model=FailurePredictionResponse)
def predict_failure(data: FailurePredictionRequest):
    """Predit la probabilite de panne d'une machine."""
    raise HTTPException(status_code=501, detail="Not implemented")
