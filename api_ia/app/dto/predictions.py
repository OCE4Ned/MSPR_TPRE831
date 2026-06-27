from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    """
    Source de vérité du schéma de features.
    Ajouter/retirer/renommer un champ ici, c'est l'unique geste à faire.
    FEATURE_COLUMNS, le DataFrame d'inférence et le contrat MLflow suivent.
    """
    cycle_time_sec: float
    temperature_C: float
    vibration_mms: float
    sound_dB: float
    oil_level_pct: float
    coolant_level_pct: float
    hydraulic_pressure_bar: float
    coolant_flow_L_min: float
    heat_index: float
    power_consumption_kW: float
    operational_hours: float
    error_codes_last_30_days: int
    sensor_anomaly_score: float
    ai_override_events: int
    flag_temperature_high: bool
    flag_vibration_high: bool
    flag_sound_high: bool
    flag_oil_low: bool
    flag_coolant_low: bool
    flag_pressure_low: bool
    flag_coolant_flow_low: bool
    flag_heat_high: bool
    flag_power_high: bool
    flag_error_codes_high: bool
    flag_anomaly_high: bool
    degradation_score: float
    degradation_rate_pct: float
    predicted_failure_probability: float
    remaining_useful_life_days: float
    failure_within_7_days: bool
    maintenance_required_within_45_days: bool


class MachineFeatures(BaseModel):
    """Snapshot reçu par l'API : identité + lecture capteurs."""
    machine_id: str
    site: str
    timestamp: datetime
    sensors: SensorReading


class MachineSequence(BaseModel):
    machine_id: str
    site: str
    readings: list[SensorReading] = Field(..., min_length=10, max_length=200)


class StateResponse(BaseModel):
    machine_id: str
    state: Literal["normal", "at_risk"]
    risk_score: float = Field(..., ge=0, le=1)
    model_name: str
    model_version: str


class RulResponse(BaseModel):
    machine_id: str
    remaining_useful_life_days: float
    model_name: str
    model_version: str


class AnomalyResponse(BaseModel):
    machine_id: str
    is_anomaly: bool
    anomaly_score: float
    model_name: str
    model_version: str


class BatchStateRequest(BaseModel):
    items: list[MachineFeatures] = Field(..., min_length=1, max_length=500)

class BatchStateResponse(BaseModel):
    items: list[StateResponse]