from fastapi import APIRouter

router = APIRouter(
    prefix="/prediction",
    tags=["prediction"],
)

@router.post("/")
async def make_prediction(data: dict):
    prediction_result = {"prediction": "result"}
    return prediction_result