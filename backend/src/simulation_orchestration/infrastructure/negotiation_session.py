"""Runtime ACL from SimulationOrchestration to NegotiationSession (issue #415).

The graph owns sequencing only. This adapter turns a turn command into the public negotiation use
cases: ensure a round, ensure an evidenced position, take one turn, then close the round when every
bound actor is accounted for.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from negotiation_session.application.commands import (
    CloseRoundRequest,
    OpenRoundRequest,
    SubmitInitialPositionRequest,
    TakeNegotiationTurnRequest,
)
from negotiation_session.application.services import (
    CloseRound,
    GetSimulationRun,
    OpenRound,
    SubmitInitialPosition,
    TakeNegotiationTurn,
)
from negotiation_session.domain.entities import NegotiationRound, RoundLearning
from negotiation_session.domain.errors import PositionNotFound, RoundCapExceeded
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    EvidencePackId,
    LearningId,
    PositionId,
    Proposal,
    StakeholderId,
    TargetRef,
    TopicRef,
    TurnOutcome,
)
from negotiation_session.domain.values import (
    InvocationId as NegotiationInvocationId,
)
from negotiation_session.domain.values import (
    RunId as NegotiationRunId,
)
from simulation_orchestration.application.values import (
    NegotiationRunView,
    NegotiationTurnCommand,
    NegotiationTurnView,
    RunId,
    RunPhase,
)

EvidencePackForClaim = Callable[[str], Awaitable[str]]


class NegotiationSessionGateway:
    """Real ACL over the frozen NegotiationSession use cases; never a no-op."""

    def __init__(
        self,
        *,
        runs: GetSimulationRun,
        open_round: OpenRound,
        submit_position: SubmitInitialPosition,
        take_turn: TakeNegotiationTurn,
        close_round: CloseRound,
        evidence_pack_for: EvidencePackForClaim,
    ) -> None:
        self._runs = runs
        self._open_round = open_round
        self._submit_position = submit_position
        self._take_turn = take_turn
        self._close_round = close_round
        self._evidence_pack_for = evidence_pack_for

    async def load_state(self, run_id: RunId) -> NegotiationRunView:
        run = await self._runs.load(NegotiationRunId(str(run_id)))
        if run.is_closed:
            return NegotiationRunView(
                run_id=run_id,
                phase=RunPhase.DONE,
                round=len(run.rounds),
                next_actor=None,
                terminal=True,
            )
        current = run.rounds[-1] if run.rounds else None
        if current is not None and not current.is_closed:
            next_actor = _next_pending(current)
            round_number = current.number
        else:
            next_actor = _first_bound(run)
            round_number = len(run.rounds)
        return NegotiationRunView(
            run_id=run_id,
            phase=RunPhase.ROUNDS,
            round=round_number,
            next_actor=next_actor,
            terminal=False,
        )

    async def take_turn(self, command: NegotiationTurnCommand) -> NegotiationTurnView:
        run = await self._runs.load(NegotiationRunId(str(command.run_id)))
        actor = StakeholderId(command.actor_id)
        topic = _topic(run)
        if run.is_closed:
            return _turn_view(command, None, terminal=True)

        if not run.rounds or run.rounds[-1].is_closed:
            try:
                await self._open_round.execute(OpenRoundRequest(run_id=run.id))
            except RoundCapExceeded:
                run = await self._runs.load(run.id)
                return _turn_view(command, None, terminal=run.is_closed)
            run = await self._runs.load(run.id)
            if run.is_closed:
                return _turn_view(command, None, terminal=True)

        pack_id = await self._evidence_pack_for(run.mandate.question)
        try:
            run.open_position(actor, topic)
        except PositionNotFound:
            await self._submit_position.execute(
                SubmitInitialPositionRequest(
                    run_id=run.id,
                    stakeholder_id=actor,
                    topic=topic,
                    stance=ArgumentStance.SUPPORT,
                    proposal=Proposal(summary=f"Position of {actor} on {topic}"),
                    evidence_ids=(EvidencePackId(pack_id),),
                )
            )
            run = await self._runs.load(run.id)

        argument = await self._take_turn.execute(
            TakeNegotiationTurnRequest(
                run_id=run.id,
                stakeholder_id=actor,
                target=TargetRef(topic=topic),
                stance=ArgumentStance.SUPPORT,
                text=command.text or _fallback_text(actor, topic),
                evidence_ids=(EvidencePackId(pack_id),),
                invocation_id=NegotiationInvocationId(str(command.invocation_id)),
            )
        )
        run = await self._runs.load(run.id)
        current = run.rounds[-1]
        if not run.is_closed and _next_pending(current) is None:
            await self._close_round.execute(
                CloseRoundRequest(
                    run_id=run.id,
                    learning=RoundLearning.capture(
                        learning_id=LearningId(f"lrn_{run.id}_{current.number}"),
                        round_number=current.number,
                        insights=(),
                    ),
                )
            )
            run = await self._runs.load(run.id)
        return _turn_view(
            command, PositionId(str(argument.position_id)) if False else None, run.is_closed
        )

    async def close_run(self, run_id: RunId) -> None:
        run = await self._runs.load(NegotiationRunId(str(run_id)))
        if run.is_closed:
            return
        current = run.rounds[-1]
        if current.is_closed:
            return
        await self._close_round.execute(
            CloseRoundRequest(
                run_id=run.id,
                learning=RoundLearning.capture(
                    learning_id=LearningId(f"lrn_{run.id}_{current.number}"),
                    round_number=current.number,
                    insights=(),
                ),
            )
        )


def _topic(run: SimulationRun) -> TopicRef:
    return TopicRef(run.mandate.question)


def _first_bound(run: SimulationRun) -> str | None:
    order = run.turn_order()
    return str(order[0].stakeholder) if order else None


def _next_pending(round_: NegotiationRound) -> str | None:
    for assignment in round_.turn_order:
        if assignment.outcome is TurnOutcome.PENDING:
            return str(assignment.stakeholder)
    return None


def _turn_view(
    command: NegotiationTurnCommand, position_id: str | None, terminal: bool
) -> NegotiationTurnView:
    return NegotiationTurnView(
        run_id=command.run_id,
        round=command.round,
        actor_id=command.actor_id,
        position_id=position_id,
        terminal=terminal,
    )


def _fallback_text(actor: StakeholderId, topic: TopicRef) -> str:
    return f"{actor} supports a negotiated solution on {topic}."
