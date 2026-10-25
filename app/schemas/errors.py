"""Consistent API error payloads."""

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-readable explanation safe for clients.")


class ErrorResponse(BaseModel):
    detail: ErrorBody
