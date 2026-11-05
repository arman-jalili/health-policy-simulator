"""Composition root for IdentityAccess (ADR-001).

Canonical: .pi/architecture/modules/identity-access.md

Selects the adapter family once at boot: PostgreSQL uses the hashed key store behind a unit of
work; memory mode uses the explicit in-memory repository. The guard, admin router and health shell
read the container from ``app.state.identity_access``.
"""

from __future__ import annotations

from dataclasses import dataclass

from identity_access.infrastructure.demo import LoopbackDemoPolicy
from identity_access.infrastructure.key_resolver import KeyResolver
from identity_access.infrastructure.key_store import HashedApiKeyStore
from identity_access.infrastructure.keys import Sha256ApiKeyFactory
from identity_access.infrastructure.readiness import AlwaysReadyReadiness, DatabaseReadiness
from identity_access.infrastructure.repository.memory import InMemoryApiKeyRepository
from identity_access.infrastructure.repository.ports import ApiKeyRepository
from identity_access.infrastructure.repository.uow import UnitOfWorkApiKeyRepository
from identity_access.interfaces.ports import (
    ApiKeyAdminPort,
    DemoModePolicy,
    PrincipalPort,
    ReadinessPort,
)
from shared.config import Settings
from shared.db import Database, UnitOfWork
from shared.enums import Persistence


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
    """Select and construct the adapters for the configured persistence family."""
    repository: ApiKeyRepository
    readiness: ReadinessPort

    if settings.persistence is Persistence.POSTGRES:
        if database is None:
            raise ValueError("PERSISTENCE=postgres requires a Database for identity-access")
        repository = UnitOfWorkApiKeyRepository(UnitOfWork(database.session_factory))
        readiness = DatabaseReadiness(database, settings.db_connect_timeout_s)
    else:
        repository = InMemoryApiKeyRepository()
        readiness = AlwaysReadyReadiness()

    store = HashedApiKeyStore(repository, Sha256ApiKeyFactory())
    return IdentityAccessContainer(
        principal_port=KeyResolver(store),
        api_key_admin=store,
        readiness=readiness,
        demo_policy=LoopbackDemoPolicy(),
    )
