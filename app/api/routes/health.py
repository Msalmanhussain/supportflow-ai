"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Response, status

import app.database as database
from app import __version__
from app.config import get_settings
from app.schemas.health import HealthResponse, ReadyResponse
from app.services.readiness import check_readiness

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Process liveness",
)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={
        503: {
            "model": ReadyResponse,
            "description": "Database unavailable or migrations not current.",
        }
    },
    summary="Database connectivity and migration readiness",
)
def ready(response: Response) -> ReadyResponse:
    # Use module attribute access so tests that call reset_engine() are visible.
    result = check_readiness(database.engine)
    payload = ReadyResponse(
        status="ready" if result.ready else "not_ready",
        database=result.database,
        migrations=result.migrations,
        detail=result.detail,
    )
    if not result.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload
