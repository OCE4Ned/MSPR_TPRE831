from fastapi import FastAPI
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    prediction_model_path: str = "models/prediction_model.h5"
    classification_model_path: str = "models/classification_model.h5"