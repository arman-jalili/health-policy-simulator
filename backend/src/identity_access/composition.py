"""Composition contract for IdentityAccess (ADR-001).

Canonical: .pi/architecture/modules/identity-access.md

The container is frozen now; issue #41 binds the concrete resolvers, key store and readiness probe
and mounts the router in ``shared.app``.
"""

from __future__ import annotations

from dataclasses import dataclass

from identity_access.interfaces.ports import (
    ApiKeyAdminPort,
    DemoModePolicy,
    PrincipalPort,
    ReadinessPort,
)
from shared.config import Settings
from shared.db import Database


@dataclass(frozen=True, slots=True)
class IdentityAccessContainer:
    """Ports the API shell reads from ``app.state.identity_access``."""

    principal_port: PrincipalPort
    api_key_admin: ApiKeyAdminPort
    readiness: ReadinessPort
    demo_policy: DemoModePolicy


def build_identity_access_container(
    settings: Settings,
    database: Database | None = None,
) -> IdentityAccessContainer:
    """Select and construct the adapters for the configured auth mode."""
    # TODO(issue #41): wire KeyResolver/DemoResolver, ApiKeyStore and the readiness probe.
    raise NotImplementedError(
        f"TODO(issue #41): wire identity-access for auth_mode={settings.auth_mode!s} "
        f"and {'postgres' if database is not None else 'no database'}"
    )
