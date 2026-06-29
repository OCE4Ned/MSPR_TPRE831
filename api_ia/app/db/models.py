from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class PredictionRecord(SQLModel, table=True):
    """FACT_AI_PREDICTIONS — one row per inference served by the API."""

    __tablename__ = "FACT_AI_PREDICTIONS"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    machine_id: str = Field(index=True)
    site: str | None = Field(default=None, index=True)
    action: str = Field(index=True)  # state | rul | rul_seq | anomaly
    model_name: str
    model_version: str
    model_alias: str | None = None
    input: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    output: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
