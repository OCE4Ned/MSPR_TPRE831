from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from app.config import get_settings
from app.services.model_registry import ModelRegistry

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
settings = get_settings()

def get_registry(request: Request) -> ModelRegistry:
    return request.app.state.registry


def verify_api_key(key: str | None = Depends(api_key_header)) -> None:
    if key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )