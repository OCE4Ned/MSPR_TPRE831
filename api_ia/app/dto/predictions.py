from pydantic import BaseModel, Field

class PredictionRequest(BaseModel):
    """
    Request model for making predictions.
    """
    input_data: list[float] = Field(..., description="Input data for prediction")

class PredictionResponse(BaseModel):
    """
    Response model for prediction results.
    """
    prediction: float = Field(..., description="The predicted value")