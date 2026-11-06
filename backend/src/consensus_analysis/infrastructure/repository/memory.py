"""In-memory projection adapters (issue #321).

These are projections, not a source of truth: the store keeps the last derived rows per run and can
be replaced wholesale by a rebuild. They exist so the context is reachable at runtime before the
PostgreSQL projection tables land, and so an end-to-end proof does not need a database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from consensus_analysis.domain.compromise_package import CompromisePackage
from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.events import DomainEvent
from consensus_analysis.domain.scenario import Scenario
from consensus_analysis.domain.values import (
    ConsensusId,
    PackageId,
    RunId,
    ScenarioId,
)


class InMemoryConsensusRepository:
    """Keyed by run and topic; a rebuild replaces a run's rows rather than mutating them."""

    def __init__(self) -> None:
        self._rows: dict[tuple[RunId, str], ConsensusRecord] = {}

    async def get(self, consensus_id: ConsensusId) -> ConsensusRecord | None:
        return next(
            (row for row in self._rows.values() if row.id == consensus_id),
            None,
        )

    async def save(self, record: ConsensusRecord) -> None:
        self._rows[(record.run_id, str(record.topic))] = record

    async def for_run(self, run_id: RunId) -> list[ConsensusRecord]:
        return [
            row
            for (stored_run, _), row in sorted(
                self._rows.items(), key=lambda item: (str(item[0][0]), int(item[1].log_position))
            )
            if stored_run == run_id
        ]

    async def replace_for_run(self, run_id: RunId, records: Sequence[ConsensusRecord]) -> None:
        for key in [key for key in self._rows if key[0] == run_id]:
            del self._rows[key]
        for record in records:
            self._rows[(record.run_id, str(record.topic))] = record


class InMemoryPackageRepository:
    def __init__(self) -> None:
        self._packages: dict[PackageId, CompromisePackage] = {}

    async def get(self, package_id: PackageId) -> CompromisePackage | None:
        return self._packages.get(package_id)

    async def save(self, package: CompromisePackage) -> None:
        self._packages[package.id] = package

    async def for_run(self, run_id: RunId) -> list[CompromisePackage]:
        return [package for package in self._packages.values() if package.run_id == run_id]


class InMemoryScenarioRepository:
    def __init__(self) -> None:
        self._scenarios: dict[ScenarioId, Scenario] = {}

    async def get(self, scenario_id: ScenarioId) -> Scenario | None:
        return self._scenarios.get(scenario_id)

    async def save(self, scenario: Scenario) -> None:
        self._scenarios[scenario.id] = scenario

    async def for_package(self, package_id: PackageId) -> list[Scenario]:
        return [
            scenario for scenario in self._scenarios.values() if scenario.package_id == package_id
        ]


class InMemoryEventPublisher:
    """Collects drained events; the outbox relay replaces it in PostgreSQL mode."""

    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(self, events: Sequence[DomainEvent], *, trace_id: str | None = None) -> None:
        self.published.extend(events)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class SequentialIdFactory:
    """Deterministic within a process, unique enough for projections."""

    def __init__(self) -> None:
        self._counter = 0

    def new_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter:06d}"


class NoopUnitOfWork:
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[object]:
        yield None
