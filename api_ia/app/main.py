import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from app.routes import prediction_route, models_route, metrics_route
from app.config import get_settings
from app.services.model_registry import ModelRegistry

from prometheus_fastapi_instrumentator import Instrumentator

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MECHA AI API")
    registry = ModelRegistry(
        tracking_uri=settings.mlflow_tracking_uri,
        tracking_username=settings.mlflow_tracking_username,
        tracking_password=settings.mlflow_tracking_password,
    )

    try:
        for key, spec in settings.models.items():
            registry.load(key, spec.name, spec.alias)
    except Exception:
        logger.exception("Failed to load models at startup")
        raise

    app.state.registry = registry
    app.state.ready = True
    logger.info("Models loaded, API ready")

    yield

    logger.info("Shutting down MECHA AI API")
    app.state.ready = False


app = FastAPI(
    title="MECHA AI API",
    description="Predictive maintenance API for MECHA",
    version="0.1.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)

app.include_router(prediction_route.router, prefix="/api/v1")
app.include_router(models_route.router, prefix="/api/v1")
app.include_router(metrics_route.router, prefix="/api/v1")

def main():
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.env)

if __name__ == "__main__":
    main()