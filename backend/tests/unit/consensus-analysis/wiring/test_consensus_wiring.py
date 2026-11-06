"""Contract freeze: wiring and the API surface (issue #305, implements #320)."""

from __future__ import annotations

from typing import Any

from tests.unit.consensus_analysis_contract_helpers import (
    SRC,
    annotation_names,
    domain_python_files,
    imported_modules,
    parameter_names,
)

from consensus_analysis.application.services import HandleRunClosed
from consensus_analysis.composition import ConsensusAnalysisContainer, build_container
from consensus_analysis.interfaces.http.deps import (
    ConsensusAnalysisContainer as HttpContainer,
)
from consensus_analysis.interfaces.http.router import router


def _routes() -> dict[tuple[str, str], Any]:
    return {
        (method, getattr(route, "path", "")): route
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_http_contract_is_exact() -> None:
    routes = _routes()
    expected = {
        ("POST", "/api/v1/runs/{run_id}/analysis:derive"),
        ("GET", "/api/v1/runs/{run_id}/consensus"),
        ("GET", "/api/v1/runs/{run_id}/conflicts/open"),
        ("POST", "/api/v1/runs/{run_id}/packages"),
        ("GET", "/api/v1/runs/{run_id}/packages"),
        ("POST", "/api/v1/packages/{package_id}/scenarios"),
        ("GET", "/api/v1/packages/{package_id}/comparison"),
    }
    assert set(routes) == expected
    assert routes[("POST", "/api/v1/runs/{run_id}/packages")].status_code == 201
    assert routes[("POST", "/api/v1/packages/{package_id}/scenarios")].status_code == 201
    assert routes[("POST", "/api/v1/runs/{run_id}/analysis:derive")].status_code is None
    assert routes[("GET", "/api/v1/runs/{run_id}/consensus")].status_code is None


def test_every_route_declares_its_scope() -> None:
    for (method, path), route in _routes().items():
        expected = "runs:write" if method == "POST" else "runs:read"
        assert route.openapi_extra == {"x-required-scope": expected}, path


def test_container_and_factory_are_frozen() -> None:
    assert annotation_names(ConsensusAnalysisContainer) == [
        "derive_consensus",
        "get_consensus",
        "list_unresolved_conflicts",
        "compose_compromise_package",
        "list_packages",
        "assess_impact",
        "compare_scenarios",
        "rebuild_projections",
        "handle_run_closed",
    ]
    assert annotation_names(HttpContainer) == annotation_names(ConsensusAnalysisContainer)
    assert parameter_names(build_container) == [
        "settings",
        "database",
        "consensus",
        "packages",
        "scenarios",
        "log",
        "powers",
        "mandate",
        "estimation",
        "catalogue",
        "components",
        "llm",
        "rebuilder",
        "ranker",
        "events",
        "clock",
        "ids",
        "uow",
    ]


def test_the_run_closed_subscriber_is_a_thin_entry_point() -> None:
    """One collaborator only: the derivation use case it delegates to (AC 12)."""
    assert parameter_names(HandleRunClosed.execute) == ["self", "request"]
    subscriber = HandleRunClosed(derive=None)  # type: ignore[arg-type]
    assert len(subscriber.collaborators()) == 1


def test_the_domain_layer_imports_no_outer_layer() -> None:
    forbidden_prefixes = (
        "consensus_analysis.application",
        "consensus_analysis.infrastructure",
        "consensus_analysis.interfaces",
    )
    for path in domain_python_files():
        relative = path.relative_to(SRC).as_posix()
        for module in imported_modules(relative):
            assert not module.startswith(forbidden_prefixes), f"{relative} imports {module}"
            assert module.split(".")[0] in {
                "__future__",
                "collections",
                "dataclasses",
                "datetime",
                "decimal",
                "enum",
                "hashlib",
                "json",
                "shared",
                "typing",
            } or module.startswith("consensus_analysis.domain"), f"{relative} imports {module}"


# ── issue #320: closing a run produces rows with no API call ───────────────────────────────────

from collections.abc import AsyncIterator, Sequence  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

import pytest  # noqa: E402

from consensus_analysis.application.commands import (  # noqa: E402
    DeriveConsensusRequest,
    GetConsensusRequest,
    ListPackagesRequest,
    ListUnresolvedConflictsRequest,
    RunClosedRequest,
)
from consensus_analysis.application.services import (  # noqa: E402
    DeriveConsensus,
    GetConsensus,
    ListPackages,
    ListUnresolvedConflicts,
)
from consensus_analysis.domain.compromise_package import CompromisePackage  # noqa: E402
from consensus_analysis.domain.consensus_record import ConsensusRecord  # noqa: E402
from consensus_analysis.domain.values import (  # noqa: E402
    AgendaItem,
    ConsensusId,
    ConsensusOutcomeKind,
    ConsensusThreshold,
    LogPosition,
    PackageId,
    ProposalClass,
    RunId,
    StakeholderId,
    Stance,
    StanceSnapshot,
    TopicRef,
)
from consensus_analysis.infrastructure.projection import LogFoldingRebuilder  # noqa: E402

RUN = RunId("run_42")
WAITING = TopicRef("waiting_times")
BUDGET = TopicRef("budget_frame")


class _Ids:
    _next = 0

    def new_id(self, prefix: str) -> str:
        type(self)._next += 1
        return f"{prefix}_{type(self)._next}"


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


class _UnitOfWork:
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[object]:
        yield None


class _Events:
    def __init__(self) -> None:
        self.published: list[object] = []

    async def publish(self, events: Sequence[object], *, trace_id: str | None = None) -> None:
        self.published.extend(events)


class _Consensus:
    """Stands in for the projection table; the only writer is the derivation."""

    def __init__(self) -> None:
        self.rows: list[ConsensusRecord] = []

    async def get(self, consensus_id: ConsensusId) -> ConsensusRecord | None:
        return next((row for row in self.rows if row.id == consensus_id), None)

    async def save(self, record: ConsensusRecord) -> None:
        self.rows = [row for row in self.rows if row.topic != record.topic] + [record]

    async def for_run(self, run_id: RunId) -> list[ConsensusRecord]:
        return list(self.rows)

    async def replace_for_run(self, run_id: RunId, records: Sequence[ConsensusRecord]) -> None:
        self.rows = [row for row in records if row.run_id == run_id]


class _Log:
    async def agenda(self, run_id: RunId) -> Sequence[AgendaItem]:
        return (
            AgendaItem(topic=WAITING, proposal_class=ProposalClass.SERVICE_CATALOGUE),
            AgendaItem(topic=BUDGET, proposal_class=ProposalClass.BUDGET_FRAME),
        )

    async def stances(self, run_id: RunId) -> Sequence[StanceSnapshot]:
        def snapshot(key: str, topic: TopicRef, stance: Stance, position: int) -> StanceSnapshot:
            return StanceSnapshot(
                stakeholder=StakeholderId(key),
                stance=stance,
                topic=topic,
                log_position=LogPosition(position),
            )

        return (
            snapshot("stk_1", WAITING, Stance.SUPPORT, 0),
            snapshot("stk_2", WAITING, Stance.OPPOSE, 1),
            snapshot("stk_3", BUDGET, Stance.SUPPORT, 2),
            snapshot("stk_bva", BUDGET, Stance.SUPPORT, 3),
        )

    async def position_of(
        self, run_id: RunId, stakeholder: StakeholderId, topic: TopicRef
    ) -> LogPosition | None:
        return None


class _Powers:
    async def veto_classes(
        self, stakeholder_ids: Sequence[StakeholderId]
    ) -> dict[StakeholderId, frozenset[ProposalClass]]:
        return {StakeholderId("stk_bva"): frozenset({ProposalClass.BUDGET_FRAME})}


class _Mandate:
    async def threshold(self, run_id: RunId) -> ConsensusThreshold:
        return ConsensusThreshold.from_mandate(0.6)


class _Packages:
    async def get(self, package_id: PackageId) -> CompromisePackage | None:
        return None

    async def save(self, package: CompromisePackage) -> None:
        return None

    async def for_run(self, run_id: RunId) -> list[CompromisePackage]:
        return []


def _derive(consensus: _Consensus, events: _Events) -> DeriveConsensus:
    return DeriveConsensus(
        consensus=consensus,
        log=_Log(),
        powers=_Powers(),
        mandate=_Mandate(),
        rebuilder=LogFoldingRebuilder(ids=_Ids()),
        events=events,
        clock=_Clock(),
        ids=_Ids(),
        uow=_UnitOfWork(),
    )


async def test_closing_a_run_produces_consensus_rows_with_no_api_call() -> None:
    consensus, events = _Consensus(), _Events()
    subscriber = HandleRunClosed(derive=_derive(consensus, events))

    result = await subscriber.execute(RunClosedRequest(run_id=RUN, condition="round_cap"))

    assert result.records == 2
    assert {str(row.topic) for row in consensus.rows} == {"waiting_times", "budget_frame"}
    assert events.published, "the audit events must reach the outbox in the same transaction"


async def test_the_derivation_blocks_the_vetoed_class_even_after_a_run_closes() -> None:
    consensus, events = _Consensus(), _Events()
    await _derive(consensus, events).execute(DeriveConsensusRequest(run_id=RUN))

    budget = next(row for row in consensus.rows if row.topic == BUDGET)
    assert budget.outcome is not None
    assert budget.outcome.kind is ConsensusOutcomeKind.VETO_BLOCKED


async def test_deriving_twice_does_not_double_the_rows_or_the_events() -> None:
    consensus, events = _Consensus(), _Events()
    derive = _derive(consensus, events)

    await derive.execute(DeriveConsensusRequest(run_id=RUN))
    first_events = len(events.published)
    await derive.execute(DeriveConsensusRequest(run_id=RUN))

    assert len(consensus.rows) == 2
    assert len(events.published) == 2 * first_events


async def test_derived_rows_rebuild_from_the_log_unchanged() -> None:
    from consensus_analysis.application.commands import RebuildProjectionsRequest
    from consensus_analysis.application.services import RebuildProjections

    consensus, events = _Consensus(), _Events()
    await _derive(consensus, events).execute(DeriveConsensusRequest(run_id=RUN))

    rebuild = RebuildProjections(
        consensus=consensus,
        log=_Log(),
        powers=_Powers(),
        rebuilder=LogFoldingRebuilder(ids=_Ids()),
        uow=_UnitOfWork(),
    )
    result = await rebuild.execute(RebuildProjectionsRequest(run_id=RUN, verify_only=True))

    assert result.records == 2


async def test_the_read_side_returns_the_projection_without_recomputing() -> None:
    consensus, events = _Consensus(), _Events()
    await _derive(consensus, events).execute(DeriveConsensusRequest(run_id=RUN))

    records = await GetConsensus(consensus=consensus).execute(GetConsensusRequest(run_id=RUN))
    conflicts = await ListUnresolvedConflicts(consensus=consensus).execute(
        ListUnresolvedConflictsRequest(run_id=RUN)
    )
    packages = await ListPackages(packages=_Packages()).execute(ListPackagesRequest(run_id=RUN))

    assert {str(row.topic) for row in records.records} == {"waiting_times", "budget_frame"}
    waiting = next(row for row in records.records if str(row.topic) == "waiting_times")
    assert waiting.outcome is ConsensusOutcomeKind.PARTIAL
    assert len(waiting.minorities) == 1
    assert conflicts.conflicts == ()
    assert packages.packages == ()


async def test_a_missing_mandate_threshold_stops_the_derivation() -> None:
    from consensus_analysis.domain.errors import ConsensusAnalysisUnavailable

    class _NoMandate:
        async def threshold(self, run_id: RunId) -> ConsensusThreshold:
            raise ConsensusAnalysisUnavailable("no mandate for run")

    derive = DeriveConsensus(
        consensus=_Consensus(),
        log=_Log(),
        powers=_Powers(),
        mandate=_NoMandate(),
        rebuilder=LogFoldingRebuilder(ids=_Ids()),
        events=_Events(),
        clock=_Clock(),
        ids=_Ids(),
        uow=_UnitOfWork(),
    )

    with pytest.raises(ConsensusAnalysisUnavailable):
        await derive.execute(DeriveConsensusRequest(run_id=RUN))
