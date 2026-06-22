import logging
import os
from dataclasses import dataclass

import mlflow
from mlflow.pyfunc import PyFuncModel
from app.ml.features import FEATURE_COLUMNS

logger = logging.getLogger(__name__)


@dataclass
class LoadedModel:
    model: PyFuncModel
    name: str
    version: str
    alias: str


class ModelRegistry:
    def __init__(
        self,
        tracking_uri: str,
        tracking_username: str | None = None,
        tracking_password: str | None = None,
    ):
        if bool(tracking_username) != bool(tracking_password):
            raise ValueError("MLflow tracking username and password must be configured together")

        if tracking_username and tracking_password:
            os.environ["MLFLOW_TRACKING_USERNAME"] = tracking_username
            os.environ["MLFLOW_TRACKING_PASSWORD"] = tracking_password

        mlflow.set_tracking_uri(tracking_uri)
        self._client = mlflow.MlflowClient()
        self._models: dict[str, LoadedModel] = {}

    def load(self, key: str, name: str, alias: str) -> None:
        uri = f"models:/{name}@{alias}"
        logger.info("Loading %s from %s", key, uri)
        model = mlflow.pyfunc.load_model(uri)
        mv = self._client.get_model_version_by_alias(name, alias)
        self._models[key] = LoadedModel(model=model, name=name, version=mv.version, alias=alias)
        logger.info("Loaded %s = %s v%s", key, name, mv.version)

        expected = set(FEATURE_COLUMNS)
        sig = model.metadata.get_input_schema()
        if sig is not None:
            actual = {col.name for col in sig.inputs}
            if actual != expected:
                raise RuntimeError(
                    f"Model {name} v{mv.version} expects features {sorted(actual)} "
                    f"but API serves {sorted(expected)}"
                )

    def get(self, key: str) -> LoadedModel:
        if key not in self._models:
            raise RuntimeError(f"Model '{key}' not loaded")
        return self._models[key]

    def list(self) -> dict[str, LoadedModel]:
        return dict(self._models)