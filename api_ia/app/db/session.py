"""Database connection + session helpers.

DATABASE_URL is the only required setting. When absent the engine is None
and writes become no-ops, so the API can still serve predictions during
local development without a Postgres instance.
"""
import logging
from typing import Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine | None:
    global _engine
    if _engine is not None:
        return _engine
    url = get_settings().database_url
    if not url:
        return None
    _engine = create_engine(url, echo=False, pool_pre_ping=True)
    return _engine


def init_db() -> None:
    """Create tables for the API's own models. Safe to call at startup."""
    engine = get_engine()
    if engine is None:
        logger.info("DATABASE_URL not set, skipping schema init")
        return
    # Import side-effect: register table metadata.
    from app.db import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session | None]:
    """FastAPI dependency. Yields None when DATABASE_URL is not configured."""
    engine = get_engine()
    if engine is None:
        yield None
        return
    with Session(engine) as session:
        yield session
