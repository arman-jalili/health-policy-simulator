"""Ports and framework-free collaborator contracts (contract freeze, issue #248)."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol, runtime_checkable

from governance_compliance.application.commands import EnforceInstitutionOnlyOutputRequest
from governance_compliance.application.dto import GuardVerdictResult, ProvenanceFacts
from governance_compliance.application.events import GovernanceEvent
from governance_compliance.application.values import (
    FigureVerdict,
    InstitutionalAllowlist,
    PersonReference,
    PositionId,
)


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class UnitOfWork(Protocol):
    def transaction(self) -> AbstractAsyncContextManager[object]: ...


@runtime_checkable
class PersonNameDetector(Protocol):
    """Infrastructure NER adapter. Deterministic and model-fixed for a rule version."""

    def detect(self, text: str) -> Sequence[PersonReference]: ...


@runtime_checkable
class InstitutionResolver(Protocol):
    """Resolve an institutional mention or alias to the canonical allowlist name."""

    def resolve(self, mention: str, allowlist: InstitutionalAllowlist) -> str | None: ...


@runtime_checkable
class FigureVerdictLookup(Protocol):
    """ClaimValidation lookup; missing is not contradiction."""

    async def verdict_for(self, reference_figure_id: str) -> FigureVerdict | None: ...


@runtime_checkable
class AllowlistSource(Protocol):
    """Boot-time source of the canonical institutions-only allowlist."""

    async def load(self) -> InstitutionalAllowlist: ...


@runtime_checkable
class ProvenanceFactsSource(Protocol):
    """ACL that reads positions, arguments, invocations and claim verdicts."""

    async def load(self, position_id: PositionId) -> ProvenanceFacts | None: ...


@runtime_checkable
class InstitutionGuard(Protocol):
    """The blocking port NegotiationSession depends on before persistence."""

    async def execute(self, request: EnforceInstitutionOnlyOutputRequest) -> GuardVerdictResult: ...


@runtime_checkable
class EventPublisher(Protocol):
    async def publish(self, events: Sequence[GovernanceEvent]) -> None: ...
