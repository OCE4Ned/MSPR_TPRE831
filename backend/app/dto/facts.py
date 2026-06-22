"""Modeles SQLModel des tables de faits (couche gold).

Les tables FACT_* n'ont pas de cle naturelle simple : on ajoute une cle
technique auto-incrementee `id` (surrogate key, standard en modele en etoile).
Les colonnes *_id sont des cles etrangeres vers les dimensions, indexees
pour les filtres.
"""

from sqlmodel import Field, SQLModel


class ProductionFact(SQLModel, table=True):
    """FACT_PRODUCTION - mesures de production / TRS."""

    __tablename__ = "FACT_PRODUCTION"

    id: int | None = Field(default=None, primary_key=True)
    date_id: int = Field(index=True)
    plant_id: str = Field(index=True)
    production_line_id: str = Field(index=True)
    machine_id: str = Field(index=True)
    product_id: str = Field(index=True)
    shift_id: str = Field(index=True)
    planned_production_qty: int
    actual_production_qty: int
    good_qty: int
    scrap_qty: int
    cycle_time_sec: float
    target_cycle_time_sec: float
    production_speed: float
    downtime_minutes: float
    setup_time_minutes: float
    availability_rate: float
    performance_rate: float
    quality_rate: float
    trs: float
    scrap_rate: float


class QualityFact(SQLModel, table=True):
    """FACT_QUALITY - controles qualite."""

    __tablename__ = "FACT_QUALITY"

    id: int | None = Field(default=None, primary_key=True)
    date_id: int = Field(index=True)
    machine_id: str = Field(index=True)
    product_id: str = Field(index=True)
    defect_id: str = Field(index=True)
    dimension_measurement: float
    tolerance_min: float
    tolerance_max: float
    is_conforming: bool
    scrap_flag: bool
    rework_required: bool
    quality_score: float


class MaintenanceFact(SQLModel, table=True):
    """FACT_MAINTENANCE - evenements de maintenance."""

    __tablename__ = "FACT_MAINTENANCE"

    id: int | None = Field(default=None, primary_key=True)
    date_id: int = Field(index=True)
    machine_id: str = Field(index=True)
    maintenance_event_id: str
    maintenance_type: str
    failure_type: str
    failure_code: str
    failure_severity: str
    repair_time_minutes: float
    downtime_minutes: float
    maintenance_cost: float
    predicted_failure_probability: float
    sensor_anomaly_score: float


class EnergyFact(SQLModel, table=True):
    """FACT_ENERGY - consommation energetique."""

    __tablename__ = "FACT_ENERGY"

    id: int | None = Field(default=None, primary_key=True)
    date_id: int = Field(index=True)
    machine_id: str = Field(index=True)
    energy_consumption_kwh: float
    compressed_air_usage: float
    cooling_water_usage: float
    power_peak_kw: float
    energy_cost: float
    energy_per_good_piece: float


class AlertFact(SQLModel, table=True):
    """FACT_ALERTS - alertes machines."""

    __tablename__ = "FACT_ALERTS"

    id: int | None = Field(default=None, primary_key=True)
    date_id: int = Field(index=True)
    machine_id: str = Field(index=True)
    alert_type: str
    alert_severity: str
    alert_reason: str
    is_active: bool
