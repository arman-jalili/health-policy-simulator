"""Frozen input/output records of IdentityAccess.

Canonical: .pi/architecture/modules/identity-access.md

Framework-free DTOs. The HTTP schemas in ``interfaces/http/schemas.py`` mirror them; the plaintext
key is excluded from ``repr`` so it cannot leak into logs (ADR-005).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from identity_access.interfaces.types import Principal, ResolutionState, Role


@dataclass(frozen=True, slots=True)
class ResolutionOutcome:
    """Observable result of resolving a request credential; not persisted."""

    state: ResolutionState
    principal: Principal | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CreateApiKeyCommand:
    """Input of ``POST /api/v1/admin/keys``."""

    label: str
    role: Role


@dataclass(frozen=True, slots=True)
class IssuedApiKey:
    """Creation result. ``key`` is shown exactly once and never stored in plaintext."""

    key_id: str
    key: str = field(repr=False)
    label: str
    role: Role
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ApiKeySummary:
    """Admin listing row; the key material and hash are never exposed."""

    key_id: str
    label: str
    role: Role
    created_at: datetime
    revoked_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """One dependency probe reported by ``GET /readyz``."""

    name: str
    ok: bool
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Aggregate readiness result; ``ready`` is true only when every check passed."""

    ready: bool
    checks: tuple[ReadinessCheck, ...]


@dataclass(frozen=True, slots=True)
class LivenessReport:
    """``GET /healthz`` payload: process liveness only, never a dependency check."""

    status: str
    service: str
    version: str
