"""Pydantic representation of the uniform error envelope for OpenAPI (ADR-004).

Runtime errors are rendered by ``shared.http.errors`` from dataclasses; these models exist so the
generated OpenAPI document can describe the same shape without duplicating wording at each route.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorDetailBody(BaseModel):
    """One machine-readable reason attached to an error."""

    message: str = Field(description="Human-readable reason; never used for branching")
    field: str | None = Field(default=None, description="Request field that caused the failure")
    code: str | None = Field(default=None, description="Stable sub-code, e.g. int_parsing")


class ErrorBody(BaseModel):
    """Uniform error envelope: ``{code, message, details, trace_id}``."""

    code: str = Field(description="Stable machine code, e.g. VALIDATION_FAILED")
    message: str = Field(description="Human-readable summary")
    details: list[ErrorDetailBody] = Field(default_factory=list)
    trace_id: str = Field(description="Trace id, also returned in the X-Request-ID header")


class HealthBody(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Build the ``responses=`` mapping documenting error envelopes for a route."""
    known: dict[int, str] = {
        400: "Malformed request",
        401: "Authentication required",
        403: "Insufficient scope for this operation",
        404: "Resource not found",
        409: "Request conflicts with current state",
        422: "Request validation failed",
        429: "Too many requests",
        500: "Unexpected error",
        503: "Dependency unavailable",
    }
    return {
        status: {"model": ErrorBody, "description": known.get(status, "Error")}
        for status in status_codes
    }
