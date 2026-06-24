"""Routes liees aux alertes."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.dto.alert import Alert
from app.dto.common import AlertStatus

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert])
def list_alerts(factory_id: Optional[str] = None, status: Optional[AlertStatus] = None):
    """Retourne la liste des alertes, filtrable par usine et par statut."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{alert_id}", response_model=Alert)
def get_alert(alert_id: str):
    """Retourne le detail d'une alerte."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{alert_id}", response_model=Alert)
def update_alert_status(alert_id: str, status: AlertStatus):
    """Met a jour le statut d'une alerte."""
    raise HTTPException(status_code=501, detail="Not implemented")
