from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Le process tourne. Toujours 200."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request):
    """Les modèles sont chargés. 503 sinon."""
    if not getattr(request.app.state, "ready", False):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready"},
        )
    return {"status": "ready"}