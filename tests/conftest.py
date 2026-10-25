"""Pytest fixtures.

Database fixtures use isolated ``supportflow_test`` only and never reset
the development database. Classification unit tests can run without DB.
"""

from __future__ import annotations

import os

import pytest

# Ensure test settings before app imports resolve Settings when DB tests run.
os.environ.setdefault("APP_ENV", "test")


def _has_database_url() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


@pytest.fixture(scope="session")
def alembic_config():
    if not _has_database_url():
        pytest.skip("DATABASE_URL required for database fixtures")
    from alembic.config import Config

    return Config("alembic.ini")


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database(alembic_config):
    """Migrate the isolated test DB and seed synthetic data once per session."""
    if not _has_database_url():
        yield
        return

    from alembic import command
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.config import clear_settings_cache, get_settings
    from app.database import reset_engine
    from app.seed.run import seed_database

    clear_settings_cache()
    settings = get_settings()
    assert settings.app_env == "test"
    assert "supportflow_test" in settings.database_url, (
        "Tests must use the isolated supportflow_test database, "
        f"got DATABASE_URL host/db portion unexpected: {settings.database_url!r}"
    )

    engine = create_engine(settings.database_url, future=True)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()

    command.upgrade(alembic_config, "head")
    clear_settings_cache()
    reset_engine()

    Session = sessionmaker(bind=create_engine(settings.database_url, future=True))
    db = Session()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


@pytest.fixture()
def db_session():
    if not _has_database_url():
        pytest.skip("DATABASE_URL required for database fixtures")

    from app.config import clear_settings_cache
    from app.database import SessionLocal, reset_engine

    clear_settings_cache()
    reset_engine()

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
