"""Health and readiness schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Process liveness indicator.")
    service: str
    version: str


class ReadyResponse(BaseModel):
    status: str = Field(description="'ready' when database and migrations are OK.")
    database: str
    migrations: str
    detail: Optional[str] = None
