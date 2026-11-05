"""HTTP dependencies for IdentityAccess admin endpoints.

Canonical: .pi/architecture/modules/identity-access.md

The composition root (issue #41) binds ``app.state.identity_access``. Until it is absent, the
endpoint fails closed with a 503 rather than pretending the key store exists.
"""

from __future__ import annotations

from typing import cast

from fastapi import Request

from identity_access.interfaces.ports import ApiKeyAdminPort
from shared.errors import ServiceUnavailableError


def get_api_key_admin(request: Request) -> ApiKeyAdminPort:
    """Return the configured key-lifecycle adapter or fail closed."""
    container = getattr(request.app.state, "identity_access", None)
    admin = getattr(container, "api_key_admin", None) if container is not None else None
    if admin is None:
        raise ServiceUnavailableError(
            "The API key store is not configured",
            code="KEY_STORE_UNAVAILABLE",
        )
    return cast(ApiKeyAdminPort, admin)
