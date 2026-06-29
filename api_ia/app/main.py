import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import uvicorn

from app.routes import prediction_route, models_route, metrics_route
from app.config import get_settings
from app.db.session import init_db
from app.services.model_registry import ModelNotLoadedError, ModelRegistry
from app.metrics import models_loaded, api_ready

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

    try:
        init_db()
    except Exception:
        logger.exception(
            "Failed to initialize DB schema: predictions will be served but not persisted"
        )

    registry = ModelRegistry(
        tracking_uri=settings.mlflow_tracking_uri,
        tracking_username=settings.mlflow_tracking_username,
        tracking_password=settings.mlflow_tracking_password,
    )
    app.state.registry = registry
    app.state.ready = False

    try:
        for key, spec in settings.models.items():
            registry.load(key, spec.name, spec.alias)
        models_loaded.set(len(settings.models))
        app.state.ready = True
        api_ready.set(1)
        logger.info("Models loaded, API ready")
    except Exception:
        api_ready.set(0)
        logger.exception(
            "Failed to load models at startup : API running in degraded mode, "
            "predictions will return 503 until models are available"
        )

    yield
    logger.info("Shutting down MECHA AI API")
    app.state.ready = False


app = FastAPI(
    title="MECHA AI API",
    description="Predictive maintenance API for MECHA",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(prediction_route.router, prefix="/api/v1")
app.include_router(models_route.router, prefix="/api/v1")
app.include_router(metrics_route.router, prefix="/api/v1")


@app.exception_handler(ModelNotLoadedError)
async def _model_not_loaded_handler(_: Request, exc: ModelNotLoadedError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


Instrumentator().instrument(app).expose(app)

def main():
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.env == "development",
    )

if __name__ == "__main__":
    main()