"""Runtime ACL from SimulationOrchestration to NegotiationSession (issues #415, #423).

The graph owns sequencing only. This adapter turns a decision produced by the node into the public
negotiation use cases: ensure a round, ensure an evidenced position, take one turn, then close the
round when every bound actor is accounted for. No stance, topic or proposal is substituted here.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

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
    ClaimStatement,
    EvidencePackId,
    LearningId,
    LearningInsight,
    LearningInsightType,
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
    NegotiationTurnBriefing,
    NegotiationTurnCommand,
    NegotiationTurnView,
    RunId,
    RunPhase,
)

_STOPWORDS = frozenset({"der", "die", "das", "und", "the", "and", "of", "in", "on"})


@dataclass(frozen=True, slots=True)
class EvidenceBriefing:
    pack_id: str
    passage_ids: tuple[str, ...] = ()


EvidencePackForClaim = Callable[[str], Awaitable[EvidenceBriefing]]


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

    async def briefing(self, run_id: RunId, actor_id: str) -> NegotiationTurnBriefing:
        run = await self._runs.load(NegotiationRunId(str(run_id)))
        actor = StakeholderId(actor_id)
        topic = _topic(run)
        pack = await self._evidence_pack_for(run.mandate.question)
        previous = run.rounds[-2].learning if len(run.rounds) >= 2 else None
        binding = run.bound[actor]
        return NegotiationTurnBriefing(
            persona_name=binding.institution_name,
            topic=str(topic),
            evidence_pack_id=pack.pack_id,
            passage_ids=pack.passage_ids,
            previous_learning=(
                json.dumps(previous.to_prompt_payload(), sort_keys=True) if previous else ""
            ),
            current_stances=_current_stances(run),
            institution_code=binding.institution_code,
            interests=binding.interests,
            interest_weights=binding.interest_weights,
            constraints=binding.constraints,
            red_lines=binding.red_lines,
            veto_classes=binding.veto_classes,
        )

    async def take_turn(self, command: NegotiationTurnCommand) -> NegotiationTurnView:
        run = await self._runs.load(NegotiationRunId(str(command.run_id)))
        actor = StakeholderId(command.actor_id)
        briefing = await self.briefing(command.run_id, command.actor_id)
        topic = TopicRef(command.topic or briefing.topic)
        stance = _stance(command.stance)
        pack_id = EvidencePackId(briefing.evidence_pack_id)
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

        try:
            run.open_position(actor, topic)
        except PositionNotFound:
            await self._submit_position.execute(
                SubmitInitialPositionRequest(
                    run_id=run.id,
                    stakeholder_id=actor,
                    topic=topic,
                    stance=stance,
                    proposal=Proposal(summary=command.proposal_summary or f"{actor} on {topic}"),
                    evidence_ids=(pack_id,),
                )
            )
            run = await self._runs.load(run.id)

        await self._take_turn.execute(
            TakeNegotiationTurnRequest(
                run_id=run.id,
                stakeholder_id=actor,
                target=TargetRef(topic=topic),
                stance=stance,
                text=command.text or f"{actor} states its position on {topic}.",
                claims=tuple(ClaimStatement(text=claim) for claim in command.claims),
                evidence_ids=tuple(
                    EvidencePackId(item) for item in (command.evidence_ids or (pack_id,))
                ),
                invocation_id=NegotiationInvocationId(str(command.invocation_id)),
            )
        )
        run = await self._runs.load(run.id)
        current = run.rounds[-1]
        if not run.is_closed and _next_pending(current) is None:
            await self._close_round.execute(
                CloseRoundRequest(
                    run_id=run.id,
                    learning=_learning(run.id, current),
                )
            )
            run = await self._runs.load(run.id)
        position = run.open_position(actor, topic)
        return _turn_view(command, str(position.id), run.is_closed)

    async def close_run(self, run_id: RunId) -> None:
        run = await self._runs.load(NegotiationRunId(str(run_id)))
        if run.is_closed:
            return
        current = run.rounds[-1]
        if current.is_closed:
            return
        await self._close_round.execute(
            CloseRoundRequest(run_id=run.id, learning=_learning(run.id, current))
        )


def _topic(run: SimulationRun) -> TopicRef:
    if run.conflicts:
        return next(iter(run.conflicts))
    tokens = [
        word.strip(".,:;!?()[]")
        for word in run.mandate.question.split()
        if word.strip(".,:;!?()[]").casefold() not in _STOPWORDS
    ]
    return TopicRef(" ".join(tokens[:2]) or "Agenda")


def _first_bound(run: SimulationRun) -> str | None:
    order = run.turn_order()
    return str(order[0].stakeholder) if order else None


def _next_pending(round_: NegotiationRound) -> str | None:
    for assignment in round_.turn_order:
        if assignment.outcome is TurnOutcome.PENDING:
            return str(assignment.stakeholder)
    return None


def _current_stances(run: SimulationRun) -> str:
    if not run.rounds:
        return ""
    return ", ".join(
        f"{stakeholder}={position.stance.value}"
        for (stakeholder, _), position in sorted(
            run.rounds[-1].positions.items(), key=lambda item: str(item[0][0])
        )
        if position.is_open
    )


def _learning(run_id: object, round_: NegotiationRound) -> RoundLearning:
    opposing = sum(1 for argument in round_.arguments if argument.stance is ArgumentStance.OPPOSE)
    statement = (
        f"Round {round_.number}: {len(round_.arguments)} contributions, {opposing} opposing."
    )
    return RoundLearning.capture(
        learning_id=LearningId(f"lrn_{run_id}_{round_.number}"),
        round_number=round_.number,
        insights=(
            LearningInsight(
                insight_type=LearningInsightType.SHARED_INTEREST,
                statement=statement,
                derived_from=tuple(argument.id for argument in round_.arguments),
                round_number=round_.number,
            ),
        ),
    )


def _stance(value: str) -> ArgumentStance:
    try:
        return ArgumentStance(value.strip().lower())
    except ValueError:
        return ArgumentStance.QUALIFY


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
