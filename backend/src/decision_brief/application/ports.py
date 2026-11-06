"""Application ports: ACLs and publication gates (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Dependencies, Wiring Contract)

Every upstream context is reached through exactly one protocol whose adapter lives in
``infrastructure/acl.py``. There is no permissive default: an unbound citation resolver or
provenance gate makes publication fail with ``BriefGateUnavailable`` instead of skipping the gate.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol, runtime_checkable

from decision_brief.application.dto import CitationResolution
from decision_brief.domain.events import DomainEvent
from decision_brief.domain.projections import ConsensusProjection, RunProjection
from decision_brief.domain.values import PassageId, RunId


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
    """Persist drained domain events in the transaction that saved the aggregate."""

    async def publish(
        self, events: Sequence[DomainEvent], *, trace_id: str | None = None
    ) -> None: ...


@runtime_checkable
class RunHistorySource(Protocol):
    """ACL to NegotiationSession: one closed run as local history projections (sections 1-5)."""

    async def load(self, run_id: RunId) -> RunProjection | None: ...


@runtime_checkable
class ConsensusSource(Protocol):
    """ACL to ConsensusAnalysis: ``ConsensusView`` as local projections (sections 6-8)."""

    async def load(self, run_id: RunId) -> ConsensusProjection | None: ...


@runtime_checkable
class CitationResolver(Protocol):
    """ACL to EvidenceCorpus: resolve every passage id to its published provenance (AC 2)."""

    async def resolve(self, passage_ids: Sequence[PassageId]) -> CitationResolution: ...


@runtime_checkable
class ProvenanceDisclosureGate(Protocol):
    """ACL to GovernanceCompliance: required disclosures must exist before publication (AC 3, 4).

    A missing binding is a boot/publication failure, never a skipped gate.
    """

    async def assert_disclosed(self, run_id: RunId) -> None: ...
