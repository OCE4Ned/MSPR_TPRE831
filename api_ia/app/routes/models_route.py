from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_registry, verify_api_key
from app.config import get_settings
from app.services.model_registry import ModelRegistry

router = APIRouter(prefix="/models", tags=["models"])
settings = get_settings()

@router.get("/", dependencies=[Depends(verify_api_key)])
def list_models(registry: ModelRegistry = Depends(get_registry)):
    return {
        "classifier": {
            "name": registry.classifier.name,
            "version": registry.classifier.version,
            "alias": registry.classifier.alias,
        },
        "regressor": {
            "name": registry.regressor.name,
            "version": registry.regressor.version,
            "alias": registry.regressor.alias,
        },
    }


@router.post("/reload", dependencies=[Depends(verify_api_key)])
def reload_models(registry: ModelRegistry = Depends(get_registry)):
    try:
        registry.load_classifier(
            settings.classifier_model_name,
            settings.classifier_model_alias,
        )
        registry.load_regressor(
            settings.regressor_model_name,
            settings.regressor_model_alias,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Reload failed: {e}")
    return {"status": "reloaded"}