from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from functools import lru_cache

class ModelSpec(BaseModel):
    name: str
    alias: str = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    mlflow_tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow_tracking_username: str | None = os.getenv("MLFLOW_TRACKING_USERNAME")
    mlflow_tracking_password: str | None = os.getenv("MLFLOW_TRACKING_PASSWORD")
    api_key: str = os.getenv("API_KEY", "changeme")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    models: dict[str, ModelSpec] = {
        "state_classifier": ModelSpec(name="mecha-machine-state-classifier"),
        "rul_regressor": ModelSpec(name="mecha-rul-regressor"),
        # à venir, sans toucher au code :
        # "anomaly_detector": ModelSpec(name="mecha-anomaly-detector"),
        # "rul_lstm": ModelSpec(name="mecha-rul-lstm"),
    }

    env: str = os.getenv("ENV", "development")
    batch_size_limit: int = 500
    risk_threshold: float = 0.5
    anomaly_threshold: float = -0.1

@lru_cache()
def get_settings() -> Settings:
    return Settings()