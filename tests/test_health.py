"""Liveness and readiness tests."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.readiness import ReadinessResult


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_ready_ok_when_migrated(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert body["migrations"] == "current"


def test_ready_fails_when_database_unavailable() -> None:
    with patch(
        "app.api.routes.health.check_readiness",
        return_value=ReadinessResult(
            ready=False,
            database="unavailable",
            migrations="unknown",
            detail="OperationalError",
        ),
    ):
        with TestClient(app) as client:
            response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["database"] == "unavailable"


def test_ready_fails_when_migrations_pending() -> None:
    with patch(
        "app.api.routes.health.check_readiness",
        return_value=ReadinessResult(
            ready=False,
            database="ok",
            migrations="pending",
            detail="Database revision(s) ['(none)'] do not match head(s) ['20260318_0001'].",
        ),
    ):
        with TestClient(app) as client:
            response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["migrations"] == "pending"
