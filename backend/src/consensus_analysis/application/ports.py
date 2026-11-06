"""Application ports: ACLs, metered estimation and rebuild strategies (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Dependencies, Wiring Contract)

Every upstream context is reached through exactly one protocol here, and its adapter lives in
``infrastructure/acl.py``. There is no permissive default anywhere: an unbound veto source or
illustrative-value catalogue makes derivation fail closed rather than guess.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol, runtime_checkable

from consensus_analysis.application.dto import (
    ComparisonEntryResult,
    ModelledEstimate,
    ReferenceFigureView,
)
from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.entities import PackageComponent
from consensus_analysis.domain.events import DomainEvent
from consensus_analysis.domain.values import (
    AgendaItem,
    ConsensusThreshold,
    DocumentedExample,
    ProposalClass,
    ReferenceFigureId,
    RunId,
    ScenarioId,
    StakeholderId,
    StanceSnapshot,
)


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
class ReferenceFigures(Protocol):
    """ACL to ClaimValidation: verified figures only, never a verification verdict or document."""

    async def resolve(
        self, reference_figure_id: ReferenceFigureId
    ) -> ReferenceFigureView | None: ...


@runtime_checkable
class IllustrativeValueSource(Protocol):
    """Documentation examples that can never be persisted as an outcome (invariant 8)."""

    def examples(self) -> Sequence[DocumentedExample]: ...


@runtime_checkable
class LlmImpactEstimator(Protocol):
    """The shared metered model client (ADR-006); a direct provider SDK call is a defect."""

    async def estimate(
        self, *, scenario_id: ScenarioId, field: str, context: str
    ) -> ModelledEstimate: ...


@runtime_checkable
class ProjectionRebuilder(Protocol):
    """Fold the run log into projection rows, keyed by log position (W9, AC 4)."""

    async def rebuild(
        self,
        *,
        run_id: RunId,
        agenda: Sequence[AgendaItem],
        stances: Sequence[StanceSnapshot],
        vetoes: dict[StakeholderId, frozenset[ProposalClass]],
        threshold: ConsensusThreshold,
    ) -> Sequence[ConsensusRecord]: ...


@runtime_checkable
class ComponentCatalogue(Protocol):
    """Accepted components of a run, with the stakeholders that accepted each one."""

    async def components(self, run_id: RunId) -> Sequence[PackageComponent]: ...


@runtime_checkable
class ComparisonRanker(Protocol):
    """Rank alternatives; a comparison missing one of the three dimensions is invalid (AC 11)."""

    def rank(self, entries: Sequence[ComparisonEntryResult]) -> Sequence[ComparisonEntryResult]: ...
