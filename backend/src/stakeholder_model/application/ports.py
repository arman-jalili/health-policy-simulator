"""Ports consumed by the StakeholderModel application layer.

Canonical: .pi/architecture/modules/stakeholder-model.md

Ports isolate persistence transactions, the downstream institutional guard and the YAML persona
adapter. They are implemented in ``infrastructure/`` or by other contexts; ``domain/`` never
imports them.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol, runtime_checkable

from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import InstitutionIdentity


@runtime_checkable
class UnitOfWork(Protocol):
    """One logical transaction per use case; commits aggregate and outbox together."""

    def transaction(self) -> AbstractAsyncContextManager[object]: ...


@runtime_checkable
class Clock(Protocol):
    """Injectable time source so persona versions and positions are reproducible in tests."""

    def now(self) -> datetime: ...


@runtime_checkable
class InstitutionalGuardPort(Protocol):
    """GovernanceCompliance ACL: institutions-only guard and its published allowlist."""

    async def assert_institution_only(self, identity: InstitutionIdentity) -> None: ...

    async def publish_allowlist(self, identities: Sequence[InstitutionIdentity]) -> None: ...


@runtime_checkable
class PersonaLoaderPort(Protocol):
    """Factory contract for validated persona cards loaded at boot."""

    def load_all(self) -> list[Stakeholder]: ...

    def load(self, code: str) -> Stakeholder: ...
