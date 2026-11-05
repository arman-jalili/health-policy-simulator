"""Stable error codes of IdentityAccess (ADR-004, ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Errors subclass the shared envelope so every refusal renders as
``{code, message, details, trace_id}``. Missing, unknown and revoked credentials all use the same
401 code to avoid key enumeration.
"""

from __future__ import annotations

from shared.errors import ForbiddenError, NotFoundError, UnauthorizedError


class AuthenticationRequiredError(UnauthorizedError):
    """No key, unknown key, or revoked key in ``AUTH_MODE=strict``."""

    code = "UNAUTHENTICATED"
    default_message = "A valid API key is required"


class InsufficientScopeError(ForbiddenError):
    """The resolved principal does not carry the scope declared by the route."""

    code = "SCOPE_REQUIRED"
    default_message = "The presented key lacks the required scope"


class ApiKeyNotFoundError(NotFoundError):
    """Admin lifecycle operation addressed a key id that does not exist."""

    code = "API_KEY_NOT_FOUND"
    default_message = "API key not found"
