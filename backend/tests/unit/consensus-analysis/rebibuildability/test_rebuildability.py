"""Contract freeze: rebibuildability (issue #305, implements #312)."""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.application.dto import RebuildResult
from consensus_analysis.application.ports import ProjectionRebuilder
from consensus_analysis.application.services import SERVICE_CLASSIFICATION, RebuildProjections
from consensus_analysis.domain.errors import ProjectionRebuildFailed
from consensus_analysis.domain.repositories import ConsensusRepository


def test_a_rebuild_reports_what_it_reproduced() -> None:
    assert field_names(RebuildResult) == ["run_id", "records", "digest"]


def test_the_rebuilder_folds_the_log_into_records() -> None:
    assert parameter_names(ProjectionRebuilder.rebuild) == [
        "self",
        "run_id",
        "agenda",
        "stances",
        "vetoes",
        "threshold",
    ]
    assert SERVICE_CLASSIFICATION["ProjectionRebuilder"] == "infrastructure"


def test_the_projection_store_can_be_replaced_from_the_log() -> None:
    assert hasattr(ConsensusRepository, "replace_for_run")
    assert parameter_names(ConsensusRepository.replace_for_run) == ["self", "run_id", "records"]


def test_a_failed_reproducibility_proof_is_an_error_not_a_warning() -> None:
    assert ProjectionRebuildFailed.code == "PROJECTION_REBUILD_FAILED"


def test_the_rebuild_use_case_is_not_implemented_yet() -> None:
    service = RebuildProjections(
        consensus=None,  # type: ignore[arg-type]
        log=None,  # type: ignore[arg-type]
        powers=None,  # type: ignore[arg-type]
        rebuilder=None,  # type: ignore[arg-type]
        uow=None,  # type: ignore[arg-type]
    )
    assert len(service.collaborators()) == 5
    assert parameter_names(RebuildProjections.execute) == ["self", "request"]
    assert SERVICE_CLASSIFICATION["RebuildProjections"] == "application"


# ── issue #312: the rebuild reproduces the projection, or says why it cannot ───────────────────

from collections.abc import AsyncIterator, Sequence  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

from consensus_analysis.application.commands import RebuildProjectionsRequest  # noqa: E402
from consensus_analysis.domain.consensus_record import ConsensusRecord  # noqa: E402
from consensus_analysis.domain.values import (  # noqa: E402
    AgendaItem,
    ConsensusId,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    StakeholderId,
    Stance,
    StanceSnapshot,
    TopicRef,
)
from consensus_analysis.infrastructure.projection import LogFoldingRebuilder  # noqa: E402

RUN = RunId("run_1")
WAITING = TopicRef("waiting_times")
BUDGET = TopicRef("budget_frame")
THRESHOLD = ConsensusThreshold.from_mandate(0.6)


class _Ids:
    """Run-sequence ids, so two rebuilds never accidentally share an identity."""

    _next = 0

    def new_id(self, prefix: str) -> str:
        type(self)._next += 1
        return f"{prefix}_{type(self)._next}"


class _UnitOfWork:
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[object]:
        yield None


class _Consensus:
    def __init__(self, rows: Sequence[ConsensusRecord]) -> None:
        self.rows = list(rows)
        self.replaced: list[tuple[ConsensusRecord, ...]] = []

    async def get(self, consensus_id: ConsensusId) -> ConsensusRecord | None:
        return next((row for row in self.rows if row.id == consensus_id), None)

    async def save(self, record: ConsensusRecord) -> None:
        self.rows = [row for row in self.rows if row.topic != record.topic] + [record]

    async def for_run(self, run_id: RunId) -> list[ConsensusRecord]:
        return list(self.rows)

    async def replace_for_run(self, run_id: RunId, records: Sequence[ConsensusRecord]) -> None:
        self.replaced.append(tuple(records))
        self.rows = list(records)


class _Log:
    def __init__(self, agenda: Sequence[AgendaItem], stances: Sequence[StanceSnapshot]) -> None:
        self._agenda = tuple(agenda)
        self._stances = tuple(stances)

    async def agenda(self, run_id: RunId) -> Sequence[AgendaItem]:
        return list(self._agenda)

    async def stances(self, run_id: RunId) -> Sequence[StanceSnapshot]:
        return list(self._stances)

    async def position_of(
        self, run_id: RunId, stakeholder: StakeholderId, topic: TopicRef
    ) -> LogPosition | None:
        return next(
            (
                snapshot.log_position
                for snapshot in self._stances
                if snapshot.stakeholder == stakeholder and snapshot.topic == topic
            ),
            None,
        )


class _Powers:
    async def veto_classes(
        self, stakeholder_ids: Sequence[StakeholderId]
    ) -> dict[StakeholderId, frozenset[ProposalClass]]:
        return {StakeholderId("stk_bva"): frozenset({ProposalClass.BUDGET_FRAME})}


def _snapshot(key: str, topic: TopicRef, stance: Stance, position: int) -> StanceSnapshot:
    return StanceSnapshot(
        stakeholder=StakeholderId(key),
        stance=stance,
        topic=topic,
        recorded=True,
        log_position=LogPosition(position),
    )


def _log() -> _Log:
    agenda = [
        AgendaItem(topic=WAITING, proposal_class=ProposalClass.SERVICE_CATALOGUE),
        AgendaItem(topic=BUDGET, proposal_class=ProposalClass.BUDGET_FRAME),
    ]
    stances = [
        _snapshot("stk_1", WAITING, Stance.SUPPORT, 0),
        _snapshot("stk_2", WAITING, Stance.OPPOSE, 1),
        _snapshot("stk_3", WAITING, Stance.SUPPORT, 2),
        _snapshot("stk_4", BUDGET, Stance.SUPPORT, 3),
        _snapshot("stk_bva", BUDGET, Stance.SUPPORT, 4),
    ]
    return _Log(agenda, stances)


async def _rebuild(log: _Log) -> Sequence[ConsensusRecord]:
    return await LogFoldingRebuilder(ids=_Ids()).rebuild(
        run_id=RUN,
        agenda=await log.agenda(RUN),
        stances=await log.stances(RUN),
        vetoes=await _Powers().veto_classes(()),
        threshold=THRESHOLD,
    )


async def test_rebuilding_twice_yields_byte_identical_records() -> None:
    first = await _rebuild(_log())
    second = await _rebuild(_log())

    assert [row.digest() for row in first] == [row.digest() for row in second]
    assert [str(row.topic) for row in first] == [str(row.topic) for row in second]
    assert [row.log_position for row in first] == [row.log_position for row in second]


async def test_a_rebuild_ignores_the_order_of_the_log() -> None:
    ordered = _log()
    shuffled = _Log(list(reversed(ordered._agenda)), list(reversed(ordered._stances)))

    assert [row.digest() for row in await _rebuild(ordered)] == [
        row.digest() for row in await _rebuild(shuffled)
    ]


async def test_rows_are_keyed_by_log_position_not_by_insertion_order() -> None:
    rows = await _rebuild(_log())

    assert [(str(row.topic), int(row.log_position)) for row in rows] == [
        ("budget_frame", 3),
        ("waiting_times", 0),
    ]


async def test_the_identity_of_a_row_is_not_part_of_what_it_concluded() -> None:
    first = await _rebuild(_log())
    second = await _rebuild(_log())

    assert first[0].id != second[0].id
    assert first[0].digest() == second[0].digest()


async def test_the_rebuild_reproduces_a_persisted_projection_and_replaces_it() -> None:
    stored = _Consensus(list(await _rebuild(_log())))
    service = RebuildProjections(
        consensus=stored,
        log=_log(),
        powers=_Powers(),
        rebuilder=LogFoldingRebuilder(ids=_Ids()),
        uow=_UnitOfWork(),
    )

    result = await service.execute(RebuildProjectionsRequest(run_id=RUN))

    assert result.records == 2
    assert len(stored.replaced) == 1


async def test_verify_only_never_writes() -> None:
    stored = _Consensus(list(await _rebuild(_log())))
    service = RebuildProjections(
        consensus=stored,
        log=_log(),
        powers=_Powers(),
        rebuilder=LogFoldingRebuilder(ids=_Ids()),
        uow=_UnitOfWork(),
    )

    await service.execute(RebuildProjectionsRequest(run_id=RUN, verify_only=True))

    assert stored.replaced == []


async def test_a_drifted_row_is_reported_by_topic() -> None:
    persisted = list(await _rebuild(_log()))
    waiting_row = next(row for row in persisted if row.topic == WAITING)
    tampered = type(waiting_row)(
        **{
            **{name: getattr(waiting_row, name) for name in waiting_row.__dataclass_fields__},
            "proposal_class": ProposalClass.FEE_SCHEDULE,
        }
    )
    stored = _Consensus([tampered, *(row for row in persisted if row.topic != WAITING)])
    service = RebuildProjections(
        consensus=stored,
        log=_log(),
        powers=_Powers(),
        rebuilder=LogFoldingRebuilder(ids=_Ids()),
        uow=_UnitOfWork(),
    )

    with pytest.raises(ProjectionRebuildFailed) as raised:
        await service.execute(RebuildProjectionsRequest(run_id=RUN))

    assert "waiting_times" in raised.value.message
    assert stored.replaced == []


async def test_an_empty_projection_cannot_be_verified() -> None:
    service = RebuildProjections(
        consensus=_Consensus([]),
        log=_log(),
        powers=_Powers(),
        rebuilder=LogFoldingRebuilder(ids=_Ids()),
        uow=_UnitOfWork(),
    )

    with pytest.raises(ProjectionRebuildFailed, match="no projection rows"):
        await service.execute(RebuildProjectionsRequest(run_id=RUN))
