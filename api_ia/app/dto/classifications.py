from pydantic import BaseModel, Field

class ClassificationRequest(BaseModel):
    """
    Request model for making classifications.
    """
    input_data: list[float] = Field(..., description="Input data for classification")

class ClassificationResponse(BaseModel):
    """
    Response model for classification results.
    """
    classification: str = Field(..., description="The predicted class label")