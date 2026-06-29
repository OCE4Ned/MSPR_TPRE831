from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelSpec(BaseModel):
    name: str
    alias: str = "champion"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_tracking_username: str | None = None
    mlflow_tracking_password: str | None = None
    database_url: str | None = None
    api_key: str = "dev-key-change-me"
    log_level: str = "INFO"
    env: str = "development"

    models: dict[str, ModelSpec] = {
        "state_classifier": ModelSpec(name="mecha-failure-7d-classifier"),
        "rul_regressor": ModelSpec(name="mecha-rul-regressor"),
        # à venir, sans toucher au code :
        # "anomaly_detector": ModelSpec(name="mecha-anomaly-detector"),
        # "rul_lstm": ModelSpec(name="mecha-rul-lstm"),
    }

    batch_size_limit: int = 500
    risk_threshold: float = 0.5
    anomaly_threshold: float = -0.1


@lru_cache()
def get_settings() -> Settings:
    return Settings()
