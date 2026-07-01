"""Tests legers de la configuration de connexion (sans acceder a la base)."""

import inspect

from app.db import session as db


def test_database_url_is_postgres():
    assert db.DATABASE_URL.startswith("postgresql")


def test_engine_created():
    # L'engine est cree a l'import (sans connexion reseau).
    assert db.engine is not None
    assert db.engine.url.get_backend_name() == "postgresql"


def test_get_session_is_generator():
    assert inspect.isgeneratorfunction(db.get_session)


def test_init_db_is_callable():
    assert callable(db.init_db)
