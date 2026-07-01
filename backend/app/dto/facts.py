"""Modeles SQLModel des tables de faits (couche gold).

Les tables gold.fact_* utilisent `bronze_event_id` comme cle primaire :
c'est l'identifiant de l'evenement bronze a l'origine de la ligne de fait.
Les colonnes *_id sont des cles etrangeres vers les dimensions, indexees
pour les filtres.
"""

from sqlmodel import Field, SQLModel


class ProductionFact(SQLModel, table=True):
    """gold.fact_production - mesures de production / TRS."""

    __tablename__ = "fact_production"
    __table_args__ = {"schema": "gold"}

    bronze_event_id: int | None = Field(default=None, primary_key=True)
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
    """gold.fact_quality - controles qualite."""

    __tablename__ = "fact_quality"
    __table_args__ = {"schema": "gold"}

    bronze_event_id: int | None = Field(default=None, primary_key=True)
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
    """gold.fact_maintenance - evenements de maintenance."""

    __tablename__ = "fact_maintenance"
    __table_args__ = {"schema": "gold"}

    bronze_event_id: int | None = Field(default=None, primary_key=True)
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
    """gold.fact_energy - consommation energetique."""

    __tablename__ = "fact_energy"
    __table_args__ = {"schema": "gold"}

    bronze_event_id: int | None = Field(default=None, primary_key=True)
    date_id: int = Field(index=True)
    machine_id: str = Field(index=True)
    energy_consumption_kwh: float
    compressed_air_usage: float
    cooling_water_usage: float
    power_peak_kw: float
    energy_cost: float
    energy_per_good_piece: float


class AlertFact(SQLModel, table=True):
    """gold.fact_alerts - alertes machines."""

    __tablename__ = "fact_alerts"
    __table_args__ = {"schema": "gold"}

    bronze_event_id: int | None = Field(default=None, primary_key=True)
    date_id: int = Field(index=True)
    machine_id: str = Field(index=True)
    alert_type: str
    alert_severity: str
    alert_reason: str
    is_active: bool
