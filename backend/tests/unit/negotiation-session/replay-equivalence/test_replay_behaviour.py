"""Replay equivalence: the log fold equals the live state (issue #296)."""

from __future__ import annotations

from negotiation_session.application.commands import (
    GetSimulationRunRequest,
    ReplaySimulationHistoryRequest,
)
from negotiation_session.application.services import GetSimulationRun, ReplaySimulationHistory
from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    ConsensusLevel,
    EvidencePackId,
    LearningId,
    MandateId,
    Proposal,
    RevisionReason,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingConditionName,
    TargetRef,
    TopicRef,
)
from negotiation_session.infrastructure.repository.memory import (
    InMemoryRunEventLog,
    InMemorySimulationRunRepository,
)

STAKEHOLDER_A = StakeholderId("stk_a")
STAKEHOLDER_B = StakeholderId("stk_b")
TOPIC = TopicRef("costs")


def _evidence(pack: str = "pack_1") -> ClaimEvidence:
    return ClaimEvidence(EvidencePackId(pack), "psg_1", "support")


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
        bound={
            STAKEHOLDER_A: StakeholderBinding(STAKEHOLDER_A, "A", "A"),
            STAKEHOLDER_B: StakeholderBinding(STAKEHOLDER_B, "B", "B"),
        },
    )
    return run


async def _sync(
    run: SimulationRun,
    repository: InMemorySimulationRunRepository,
    event_log: InMemoryRunEventLog,
) -> None:
    await event_log.append(run.id, run.drain_events())
    await repository.save(run)


async def test_folding_the_log_reproduces_the_live_state_at_every_round() -> None:
    repository = InMemorySimulationRunRepository()
    event_log = InMemoryRunEventLog()
    run = _run()
    await _sync(run, repository, event_log)

    run.open_round()
    await _sync(run, repository, event_log)
    run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, Proposal(summary="A"), [_evidence()]
    )
    await _sync(run, repository, event_log)
    run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.SUPPORT,
        "Round one.",
        (),
        [_evidence()],
    )
    await _sync(run, repository, event_log)
    run.take_turn(
        STAKEHOLDER_B,
        TargetRef(topic=TOPIC),
        ArgumentStance.OPPOSE,
        "Round one counter.",
        (),
        [_evidence("pack_2")],
    )
    await _sync(run, repository, event_log)
    run.close_round(RoundLearning(LearningId("lrn_1"), 1))
    await _sync(run, repository, event_log)

    live_after_round_one = await GetSimulationRun(runs=repository).execute(
        GetSimulationRunRequest(run_id=run.id)
    )

    run.open_round()
    await _sync(run, repository, event_log)
    argument = run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.QUALIFY,
        "Round two.",
        (),
        [_evidence("pack_3")],
    )
    await _sync(run, repository, event_log)
    run.revise_position(
        STAKEHOLDER_A,
        TOPIC,
        ArgumentStance.OPPOSE,
        RevisionReason(argument_ids=(argument.id,), driver="round two evidence"),
    )
    await _sync(run, repository, event_log)
    run.record_abstention(STAKEHOLDER_B, TOPIC)
    await _sync(run, repository, event_log)
    run.close_round(RoundLearning(LearningId("lrn_2"), 2))
    await _sync(run, repository, event_log)
    run.evaluate_stopping(ConsensusLevel.SUFFICIENT)
    await _sync(run, repository, event_log)

    live_final = await GetSimulationRun(runs=repository).execute(
        GetSimulationRunRequest(run_id=run.id)
    )
    replay = await ReplaySimulationHistory(runs=repository, event_log=event_log).execute(
        ReplaySimulationHistoryRequest(run_id=run.id)
    )
    assert replay.state == live_final
    assert [item.sequence for item in replay.events] == list(range(1, len(replay.events) + 1))

    replay_round_one = await ReplaySimulationHistory(runs=repository, event_log=event_log).execute(
        ReplaySimulationHistoryRequest(run_id=run.id, until_round=1)
    )
    assert replay_round_one.state == live_after_round_one
    assert replay_round_one.until_round == 1
    assert len(replay_round_one.events) < len(replay.events)
    assert all(int(str(item.payload.get("round", 1))) <= 1 for item in replay_round_one.events)
