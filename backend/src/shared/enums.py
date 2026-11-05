"""Cross-cutting technical enums.

Domain enums (authority tiers, run phases, claim types, ...) belong to the bounded context
that owns them and are introduced with that context, not here.

Canonical: .pi/architecture/decisions/ADR-008-proportional-modeling-depth.md
"""

from __future__ import annotations

from enum import StrEnum


class Environment(StrEnum):
    """Deployment environment; drives boot-time safety checks (see ADR-005)."""

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class AuthMode(StrEnum):
    """Authentication strictness (ADR-005).

    ``DEMO`` allows anonymous reads and ``runs:write`` from localhost only.
    """

    DEMO = "demo"
    STRICT = "strict"


class LogFormat(StrEnum):
    """Log rendering format."""

    JSON = "json"
    CONSOLE = "console"


class OutboxStatus(StrEnum):
    """Lifecycle of a row in ``shared_event_outbox`` (ADR-002, ADR-003)."""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class AuditOutcome(StrEnum):
    """Outcome recorded on an audit row."""

    SUCCESS = "success"
    REFUSED = "refused"
    FAILED = "failed"
