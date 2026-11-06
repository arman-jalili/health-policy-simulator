"""Application ports: ACLs and technical collaborators (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Dependencies, Wiring Contract)

Every upstream context is reached through one of these protocols; adapters live in
``infrastructure/acl.py``. The governance guard has no permissive default: an unbound guard
makes writes fail closed (AC 14).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol, runtime_checkable

from claim_validation.interfaces.published import ClaimVerdictView
from evidence_retrieval.interfaces.published import EvidencePackView
from governance_compliance.interfaces.published import GuardVerdictView
from negotiation_session.application.progress import SseFrame
from negotiation_session.domain.events import DomainEvent
from negotiation_session.domain.values import (
    ClaimStatement,
    EvidencePackId,
    InvocationId,
    RunId,
    StakeholderId,
)
from stakeholder_model.interfaces.published import StakeholderProfileView


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class UnitOfWork(Protocol):
    def transaction(self) -> AbstractAsyncContextManager[object]: ...


@runtime_checkable
class IdFactory(Protocol):
    def new_id(self, prefix: str) -> str: ...


@runtime_checkable
class EventPublisher(Protocol):
    """Persist drained domain events in the transaction that saved the run."""

    async def publish(
        self, events: Sequence[DomainEvent], *, trace_id: str | None = None
    ) -> None: ...


@runtime_checkable
class StakeholderDirectory(Protocol):
    """Partner contract of StakeholderModel; the adapter maps it to ``StakeholderBinding``."""

    async def profile(self, stakeholder_id: StakeholderId) -> StakeholderProfileView | None: ...


@runtime_checkable
class EvidencePackReader(Protocol):
    """ACL to EvidenceRetrieval: frozen packs only, never raw hits or vectors."""

    async def frozen_pack(self, pack_id: EvidencePackId) -> EvidencePackView | None: ...


@runtime_checkable
class ClaimVerdictGate(Protocol):
    """Partner contract of ClaimValidation: verdicts gate claims before acceptance."""

    async def verdict_for(self, claim: ClaimStatement) -> ClaimVerdictView: ...


@runtime_checkable
class GovernanceGuard(Protocol):
    """ACL to GovernanceCompliance: pre-persistence guard on every write path."""

    async def enforce(
        self,
        text: str,
        *,
        run_id: RunId,
        stakeholder_id: StakeholderId,
        invocation_id: InvocationId | None = None,
    ) -> GuardVerdictView: ...


@runtime_checkable
class InvocationLookup(Protocol):
    """ACL to SimulationOrchestration: every argument carries the invocation that produced it."""

    async def require(self, run_id: RunId, invocation_id: InvocationId) -> None: ...


@runtime_checkable
class RunProgressPublisher(Protocol):
    """Publish ordered progress frames for a live run (AC 13)."""

    async def publish(self, run_id: RunId, events: Sequence[DomainEvent]) -> None: ...


@runtime_checkable
class RunProgressStream(Protocol):
    """Replay from ``last_event_id`` (exclusive) and continue live without gaps."""

    def subscribe(
        self, run_id: RunId, *, last_event_id: str | None = None
    ) -> AsyncIterator[SseFrame]: ...
