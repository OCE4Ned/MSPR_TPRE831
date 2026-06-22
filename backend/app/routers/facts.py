"""Routes des tables de faits (mesures analytiques)."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.dto.facts import (
    AlertFact,
    EnergyFact,
    MaintenanceFact,
    ProductionFact,
    QualityFact,
)

router = APIRouter(prefix="/facts", tags=["facts"])


# --- FACT_PRODUCTION --------------------------------------------------------

@router.get("/production", response_model=list[ProductionFact])
def list_production(
    plant_id: str | None = None,
    production_line_id: str | None = None,
    machine_id: str | None = None,
    date_id: int | None = None,
    session: Session = Depends(get_session),
):
    """Mesures de production (TRS, quantites, temps de cycle)."""
    query = select(ProductionFact)
    if plant_id is not None:
        query = query.where(ProductionFact.plant_id == plant_id)
    if production_line_id is not None:
        query = query.where(ProductionFact.production_line_id == production_line_id)
    if machine_id is not None:
        query = query.where(ProductionFact.machine_id == machine_id)
    if date_id is not None:
        query = query.where(ProductionFact.date_id == date_id)
    return session.exec(query).all()


# --- FACT_QUALITY -----------------------------------------------------------

@router.get("/quality", response_model=list[QualityFact])
def list_quality(
    machine_id: str | None = None,
    product_id: str | None = None,
    defect_id: str | None = None,
    date_id: int | None = None,
    session: Session = Depends(get_session),
):
    """Controles qualite (mesures, conformite, defauts)."""
    query = select(QualityFact)
    if machine_id is not None:
        query = query.where(QualityFact.machine_id == machine_id)
    if product_id is not None:
        query = query.where(QualityFact.product_id == product_id)
    if defect_id is not None:
        query = query.where(QualityFact.defect_id == defect_id)
    if date_id is not None:
        query = query.where(QualityFact.date_id == date_id)
    return session.exec(query).all()


# --- FACT_MAINTENANCE -------------------------------------------------------

@router.get("/maintenance", response_model=list[MaintenanceFact])
def list_maintenance(
    machine_id: str | None = None,
    date_id: int | None = None,
    session: Session = Depends(get_session),
):
    """Evenements de maintenance (pannes, couts, anomalies)."""
    query = select(MaintenanceFact)
    if machine_id is not None:
        query = query.where(MaintenanceFact.machine_id == machine_id)
    if date_id is not None:
        query = query.where(MaintenanceFact.date_id == date_id)
    return session.exec(query).all()


# --- FACT_ENERGY ------------------------------------------------------------

@router.get("/energy", response_model=list[EnergyFact])
def list_energy(
    machine_id: str | None = None,
    date_id: int | None = None,
    session: Session = Depends(get_session),
):
    """Consommation energetique par machine."""
    query = select(EnergyFact)
    if machine_id is not None:
        query = query.where(EnergyFact.machine_id == machine_id)
    if date_id is not None:
        query = query.where(EnergyFact.date_id == date_id)
    return session.exec(query).all()


# --- FACT_ALERTS ------------------------------------------------------------

@router.get("/alerts", response_model=list[AlertFact])
def list_alerts(
    machine_id: str | None = None,
    is_active: bool | None = None,
    alert_severity: str | None = None,
    session: Session = Depends(get_session),
):
    """Alertes machines, filtrables par machine, statut et severite."""
    query = select(AlertFact)
    if machine_id is not None:
        query = query.where(AlertFact.machine_id == machine_id)
    if is_active is not None:
        query = query.where(AlertFact.is_active == is_active)
    if alert_severity is not None:
        query = query.where(AlertFact.alert_severity == alert_severity)
    return session.exec(query).all()
