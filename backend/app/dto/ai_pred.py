"""Schemas d'entree / sortie des predictions du modele d'IA.

Ce ne sont pas des tables (pas de table=True) : juste la forme des donnees
echangees par l'endpoint de maintenance predictive.
"""

from sqlmodel import SQLModel


class FailurePredictionRequest(SQLModel):
    # Champs attendus en entree du modele de prediction de panne.
    machine_id: str
    date_id: int | None = None
    sensor_anomaly_score: float | None = None


class FailurePredictionResponse(SQLModel):
    # Resultat renvoye par le modele.
    machine_id: str
    predicted_failure_probability: float
    failure_severity: str | None = None
