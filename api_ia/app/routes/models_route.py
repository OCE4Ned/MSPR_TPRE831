from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.deps import get_registry, verify_api_key
from app.services.model_registry import ModelRegistry

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/", dependencies=[Depends(verify_api_key)])
def list_models(registry: ModelRegistry = Depends(get_registry)):
    return {
        key: {"name": loaded.name, "version": loaded.version, "alias": loaded.alias}
        for key, loaded in registry.list().items()
    }


@router.post("/reload", dependencies=[Depends(verify_api_key)])
def reload_models(registry: ModelRegistry = Depends(get_registry)):
    settings = get_settings()
    try:
        for key, spec in settings.models.items():
            registry.load(key, spec.name, spec.alias)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Reload failed: {e}")
    return {"status": "reloaded", "models": list(settings.models)}
