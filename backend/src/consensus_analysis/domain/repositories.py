"""Domain-owned repository and derivation ports (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Domain-owned repository)

Repository protocols live with the domain so application services never depend on SQLAlchemy.
Columns are out of scope: they sit behind these ports (ADR-002).

``RunLogPort`` is the only derivation input. ``replace_for_run`` exists because these tables are
projections: a rebuild writes the same rows from the log instead of editing them (invariant 1,
AC 4). ``StakeholderPowersPort`` is the ACL to veto rights: a veto is read, never inferred.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from consensus_analysis.domain.compromise_package import CompromisePackage
from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.scenario import Scenario
from consensus_analysis.domain.values import (
    AgendaItem,
    ConsensusId,
    LogPosition,
    PackageId,
    ProposalClass,
    RunId,
    ScenarioId,
    StakeholderId,
    StanceSnapshot,
    TopicRef,
)


@runtime_checkable
class ConsensusRepository(Protocol):
    """Persistence boundary of the ``ConsensusRecord`` aggregate."""

    async def get(self, consensus_id: ConsensusId) -> ConsensusRecord | None: ...

    async def save(self, record: ConsensusRecord) -> None:
        """Persist the record and append its drained events in the same transaction."""
        ...

    async def for_run(self, run_id: RunId) -> list[ConsensusRecord]: ...

    async def replace_for_run(self, run_id: RunId, records: Sequence[ConsensusRecord]) -> None:
        """Replace every projection row of a run; used by the rebuild, never by a request."""
        ...


@runtime_checkable
class CompromisePackageRepository(Protocol):
    """Persistence boundary of the ``CompromisePackage`` aggregate."""

    async def get(self, package_id: PackageId) -> CompromisePackage | None: ...

    async def save(self, package: CompromisePackage) -> None: ...

    async def for_run(self, run_id: RunId) -> list[CompromisePackage]: ...


@runtime_checkable
class ScenarioRepository(Protocol):
    """Persistence boundary of the ``Scenario`` aggregate."""

    async def get(self, scenario_id: ScenarioId) -> Scenario | None: ...

    async def save(self, scenario: Scenario) -> None: ...

    async def for_package(self, package_id: PackageId) -> list[Scenario]: ...


@runtime_checkable
class RunLogPort(Protocol):
    """ACL to the closed run log: the single, replayable derivation input."""

    async def agenda(self, run_id: RunId) -> Sequence[AgendaItem]:
        """Replay the topics of the run with the proposal class each one belongs to."""
        ...

    async def stances(self, run_id: RunId) -> Sequence[StanceSnapshot]:
        """Replay every recorded stance of the run, ordered by log position."""
        ...

    async def position_of(
        self, run_id: RunId, stakeholder: StakeholderId, topic: TopicRef
    ) -> LogPosition | None:
        """Return the log position of one stance, or ``None`` when it was never recorded."""
        ...


@runtime_checkable
class StakeholderPowersPort(Protocol):
    """ACL to veto rights published by StakeholderModel."""

    async def veto_classes(
        self, stakeholder_ids: Sequence[StakeholderId]
    ) -> dict[StakeholderId, frozenset[ProposalClass]]:
        """Return the veto map; an unknown stakeholder holds no veto, it is never assumed."""
        ...
