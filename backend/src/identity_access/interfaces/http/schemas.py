"""Request/response schemas for the admin key lifecycle (ADR-004).

Canonical: .pi/architecture/modules/identity-access.md

These mirror the framework-free DTOs in ``identity_access.interfaces.dto``. The plaintext key
appears in ``IssuedApiKeyResponse`` only; listings never include it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from identity_access.interfaces.types import Role


class CreateApiKeyRequest(BaseModel):
    """Body of ``POST /api/v1/admin/keys``."""

    label: str = Field(min_length=1, max_length=120)
    role: Role


class IssuedApiKeyResponse(BaseModel):
    """``201`` response: the plaintext key is shown exactly once."""

    key_id: str
    key: str = Field(description="Plaintext API key; returned exactly once")
    label: str
    role: Role
    created_at: datetime


class ApiKeySummaryResponse(BaseModel):
    """One row of ``GET /api/v1/admin/keys``; no secret material."""

    key_id: str
    label: str
    role: Role
    created_at: datetime
    revoked_at: datetime | None = None
