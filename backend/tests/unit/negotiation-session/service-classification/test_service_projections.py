"""Service classification: application services produce projections (issue #285)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from negotiation_session.application.commands import (
    GetSimulationRunRequest,
    ListConflictTopicsRequest,
    ListRoundLearningRequest,
    ListRoundsRequest,
    SummariseIntermediateResultRequest,
    TranslateQuestionToMandateRequest,
)
from negotiation_session.application.services import (
    GetSimulationRun,
    ListConflictTopics,
    ListRoundLearning,
    ListRounds,
    SummariseIntermediateResult,
    TranslateQuestionToMandate,
)
from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    EvidencePackId,
    LearningId,
    MandateId,
    NegotiationPhase,
    Proposal,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingConditionName,
    TargetRef,
    TopicRef,
)

STAKEHOLDER_A = StakeholderId("stk_a")
STAKEHOLDER_B = StakeholderId("stk_b")
TOPIC = TopicRef("costs")


class FakeRunRepository:
    def __init__(self, run: SimulationRun) -> None:
        self.run = run

    async def get(self, run_id: RunId) -> SimulationRun | None:
        return self.run if run_id == self.run.id else None

    async def all_ids(self) -> Sequence[RunId]:
        return (self.run.id,)

    async def save(self, run: SimulationRun) -> None:
        self.run = run


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


class FixedIds:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_fixed"


def _binding(stakeholder: StakeholderId) -> StakeholderBinding:
    return StakeholderBinding(stakeholder, stakeholder, stakeholder)


def _run() -> SimulationRun:
    run = SimulationRun.open(
        run_id=RunId("run_1"),
        mandate=NegotiationMandate(
            id=MandateId("mnd_1"),
            question="How to stabilise costs?",
            objective="Agreement",
            constraints=(),
            round_cap=5,
            stopping_conditions=(StoppingConditionName.CONSENSUS,),
            profile_version="v1",
        ),
        bound={STAKEHOLDER_A: _binding(STAKEHOLDER_A), STAKEHOLDER_B: _binding(STAKEHOLDER_B)},
    )
    run.open_round()
    run.submit_initial_position(
        STAKEHOLDER_A,
        TOPIC,
        ArgumentStance.SUPPORT,
        Proposal(summary="A"),
        [ClaimEvidence(evidence_id=EvidencePackId("pack_1"), passage_id="psg_1", stance="support")],
    )
    run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.SUPPORT,
        "We need a cap.",
        (),
        [ClaimEvidence(evidence_id=EvidencePackId("pack_1"), passage_id="psg_1", stance="support")],
    )
    run.record_abstention(STAKEHOLDER_B, TOPIC)
    run.track_conflict(TOPIC, {STAKEHOLDER_A: ArgumentStance.SUPPORT})
    run.close_round(RoundLearning(id=LearningId("lrn_1"), round_number=1))
    return run


async def test_translate_question_builds_a_bounded_mandate() -> None:
    service = TranslateQuestionToMandate(ids=FixedIds())
    result = await service.execute(
        TranslateQuestionToMandateRequest(question="How to stabilise costs?", round_cap=4)
    )
    assert result.mandate_id == "mnd_fixed"
    assert result.round_cap == 4
    assert result.question == "How to stabilise costs?"
    assert set(result.stopping_conditions) == {
        StoppingConditionName.CONSENSUS,
        StoppingConditionName.ROUND_CAP,
        StoppingConditionName.DEADLOCK,
    }
    assert len(result.mandate_hash) == 64


async def test_get_run_projects_the_live_state() -> None:
    run = _run()
    result = await GetSimulationRun(runs=FakeRunRepository(run)).execute(
        GetSimulationRunRequest(run_id=run.id)
    )
    assert result.run_id == run.id
    assert result.phase is NegotiationPhase.POSITION_FORMATION
    assert result.round == 1
    assert result.round_cap == 5
    assert not result.closed
    assert result.bound_stakeholder_ids == (STAKEHOLDER_A, STAKEHOLDER_B)
    assert len(result.open_position_ids) == 1


async def test_read_services_project_rounds_conflicts_and_learning() -> None:
    run = _run()
    repository = FakeRunRepository(run)

    rounds = await ListRounds(runs=repository).execute(ListRoundsRequest(run_id=run.id))
    assert len(rounds) == 1
    assert rounds[0].round == 1
    assert rounds[0].closed
    assert rounds[0].argument_count == 1
    assert rounds[0].abstention_count == 1

    conflicts = await ListConflictTopics(runs=repository).execute(
        ListConflictTopicsRequest(run_id=run.id)
    )
    assert len(conflicts) == 1
    assert conflicts[0].topic == TOPIC

    learning = await ListRoundLearning(runs=repository).execute(
        ListRoundLearningRequest(run_id=run.id)
    )
    assert len(learning) == 1
    assert learning[0].learning_id == LearningId("lrn_1")


async def test_summary_reports_open_conflicts_and_coalitions() -> None:
    run = _run()
    result = await SummariseIntermediateResult(runs=FakeRunRepository(run)).execute(
        SummariseIntermediateResultRequest(run_id=run.id)
    )
    assert result.run_id == run.id
    assert result.round == 1
    assert result.phase is NegotiationPhase.POSITION_FORMATION
    assert result.open_conflicts == (TOPIC,)
    assert result.coalition_ids == ()
