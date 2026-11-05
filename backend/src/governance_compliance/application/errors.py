"""Stable error codes of GovernanceCompliance (contract freeze, issue #248)."""

from __future__ import annotations

from shared.errors import (
    AppError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationFailedError,
)


class GovernanceViolationNotFound(NotFoundError):
    code = "GOVERNANCE_VIOLATION_NOT_FOUND"


class ProvenanceIncomplete(ValidationFailedError):
    """Evidence, argument or invocation facts are missing; nothing may be disclosed."""

    code = "PROVENANCE_INCOMPLETE"


class AllowlistEmpty(AppError):
    """An empty allowlist is a boot failure, never permit-all."""

    code = "ALLOWLIST_EMPTY"
    status_code = 500
    default_message = "institutional allowlist is empty"


class AllowlistContainsPerson(AppError):
    """A natural person in the allowlist is a configuration error."""

    code = "ALLOWLIST_CONTAINS_PERSON"
    status_code = 500
    default_message = "institutional allowlist contains a natural person"


class GuardVerdictRequired(ConflictError):
    """NegotiationSession attempted a write without a guard verdict."""

    code = "GUARD_VERDICT_REQUIRED"


class GuardUnavailable(ServiceUnavailableError):
    """The guard is not bound; the write path must fail closed."""

    code = "GOVERNANCE_GUARD_UNAVAILABLE"


class UnknownGovernanceRule(ValidationFailedError):
    code = "UNKNOWN_GOVERNANCE_RULE"
