"""Graph nodes that drive a real NegotiationSession run (issue #415)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal

from simulation_orchestration.application.commands import RecordAgentInvocationRequest
from simulation_orchestration.application.errors import LlmOutputUnparseable
from simulation_orchestration.application.ports import LLMClient, NegotiationGateway
from simulation_orchestration.application.services import RecordAgentInvocation
from simulation_orchestration.application.values import (
    GraphState,
    InvocationOutcome,
    LLMRequest,
    NegotiationTurnBriefing,
    NegotiationTurnCommand,
    PromptRef,
    RunPhase,
)
from simulation_orchestration.infrastructure.identity import invocation_identity

_PROMPT = PromptRef("stakeholder-turn", 1)


class NegotiationPrepareNode:
    """Read the run and move graph state into the rounds phase; no domain mutation."""

    name = "negotiation-prepare"
    phase = RunPhase.MANDATE

    def __init__(self, *, negotiation: NegotiationGateway) -> None:
        self._negotiation = negotiation

    async def execute(self, state: GraphState) -> GraphState:
        view = await self._negotiation.load_state(state.run_id)
        if view.terminal:
            return replace(state, phase=RunPhase.DONE, next_actor=None)
        if view.next_actor is None:
            raise RuntimeError(f"run {state.run_id} has no next actor to drive")
        return replace(
            state,
            phase=RunPhase.ROUNDS,
            round=view.round,
            next_actor=view.next_actor,
        )


class NegotiationTurnNode:
    """Meter one model call, then apply it through the negotiation gateway."""

    name = "negotiation-turn"
    phase = RunPhase.ROUNDS

    def __init__(
        self,
        *,
        recorder: RecordAgentInvocation,
        negotiation: NegotiationGateway,
        llm: LLMClient,
        model: str,
        synthetic: bool,
        scripted: Callable[[], bool] | None = None,
    ) -> None:
        self._recorder = recorder
        self._negotiation = negotiation
        self._llm = llm
        self._model = model
        # Read per call: a demo can switch the backend at runtime, and the echo is only acceptable
        # while the scripted variant is the one answering. `synthetic` is the boot default used when
        # no reader is injected; keeping it as a field would be an unread collaborator (W8).
        self._is_scripted = scripted or (lambda: synthetic)

    async def execute(self, state: GraphState) -> GraphState:
        actor = state.next_actor
        if actor is None:
            return replace(state, phase=RunPhase.DONE)
        briefing = await self._negotiation.briefing(state.run_id, actor)
        prompt = (
            f"Persona: {briefing.persona_name} ({actor}).\n"
            f"Agenda topic: {briefing.topic}. Round {state.round}.\n"
            f"Evidence pack: {briefing.evidence_pack_id}; passages: "
            f"{', '.join(briefing.passage_ids) or 'none'}.\n"
            f"Interests: {'; '.join(briefing.interests) or 'none'}.\n"
            f"Constraints: {'; '.join(briefing.constraints) or 'none'}.\n"
            f"Red lines: {'; '.join(briefing.red_lines) or 'none'}.\n"
            f"Veto classes: {', '.join(briefing.veto_classes) or 'none'}.\n"
            f"Current stances: {briefing.current_stances or 'none'}.\n"
            f"Previous learning: {briefing.previous_learning or 'none'}.\n"
            "Write one institutional argument in this persona's own voice, grounded in the "
            "interests, constraints and red lines above.\n"
            "Choose the stance the mandate actually requires, not the agreeable one: oppose when "
            "the measure hurts a priority interest or crosses a red line; qualify or conditionally "
            "accept when it helps only under stated conditions; support only when nothing in the "
            "card is in tension with the measure. Do not mirror the current stances just because "
            "others took them: a negotiation in which everyone agrees is a failed simulation.\n"
            'Return JSON only with keys "stance" (support|oppose|qualify|conditional_accept), '
            '"proposal" (one sentence naming the measure and its condition, if any), '
            '"claims" (array of factual statements you would defend, or []), and '
            '"argument" (3-5 sentences, concrete, no personal names, no quotations).'
        )
        is_scripted = self._is_scripted()
        started = time.perf_counter()
        response = await self._llm.complete(
            LLMRequest(
                model=self._model,
                prompt=prompt,
                prompt_ref=_PROMPT,
                parameters={"synthetic": is_scripted},
            )
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        decision = _decision(response.text, briefing, synthetic=is_scripted, prompt=prompt)
        invocation_id = invocation_identity(state.run_id, state.round, actor, "stakeholder-turn")
        await self._recorder.execute(
            RecordAgentInvocationRequest(
                invocation_id=invocation_id,
                run_id=state.run_id,
                round=state.round,
                stakeholder=actor,
                purpose="stakeholder_turn",
                model=response.model,
                prompt=_PROMPT,
                parameters={"synthetic": is_scripted, "topic": briefing.topic},
                evidence_pack_ids=(briefing.evidence_pack_id,),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_estimate=Decimal("0"),
                latency_ms=latency_ms,
                outcome=InvocationOutcome.SUCCESS,
            )
        )
        await self._negotiation.take_turn(
            NegotiationTurnCommand(
                run_id=state.run_id,
                round=state.round,
                actor_id=actor,
                invocation_id=invocation_id,
                text=decision.argument,
                topic=briefing.topic,
                stance=decision.stance,
                proposal_summary=decision.proposal,
                claims=decision.claims,
                evidence_ids=(briefing.evidence_pack_id,),
            )
        )
        view = await self._negotiation.load_state(state.run_id)
        if view.terminal:
            return replace(state, phase=RunPhase.DONE, round=view.round, next_actor=None)
        if view.next_actor is None:
            raise RuntimeError(f"run {state.run_id} is open but has no next actor")
        return replace(state, round=view.round, next_actor=view.next_actor)


@dataclass(frozen=True, slots=True)
class _Decision:
    stance: str
    proposal: str
    claims: tuple[str, ...]
    argument: str


_STANCES = frozenset({"support", "oppose", "qualify", "conditional_accept"})


def _decision(
    text: str, briefing: NegotiationTurnBriefing, *, synthetic: bool, prompt: str
) -> _Decision:
    """Parse a real JSON decision; the scripted provider gets an explainable persona policy."""
    payload = text.strip()
    if payload.startswith("```"):
        lines = payload.splitlines()
        payload = "\n".join(lines[1:-1] if len(lines) > 2 else lines[1:])
    try:
        parsed = json.loads(payload)
    except (TypeError, ValueError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}

    stance = str(parsed.get("stance") or "").strip().lower()
    argument = str(parsed.get("argument") or parsed.get("text") or "").strip()
    echoes_prompt = bool(argument) and (argument in prompt or prompt.strip() in argument)
    if stance in _STANCES and argument and not echoes_prompt:
        proposal = parsed.get("proposal")
        if isinstance(proposal, dict):
            proposal_summary = str(proposal.get("summary") or "")
        else:
            proposal_summary = str(proposal or "")
        claims = parsed.get("claims") or []
        return _Decision(
            stance=stance,
            proposal=proposal_summary or "Measured position on the agenda",
            claims=tuple(str(claim) for claim in claims if str(claim).strip()),
            argument=argument,
        )

    if not synthetic:
        reason = "prompt echo" if echoes_prompt else "no parseable stance/argument"
        raise LlmOutputUnparseable(
            f"model output was unusable ({reason}); expected JSON with stance and argument"
        )

    stance, reason = _persona_policy(briefing)
    return _Decision(
        stance=stance,
        proposal=f"{briefing.persona_name}: measured position on {briefing.topic}",
        claims=(),
        argument=(
            f"[synthetic] {briefing.persona_name} nimmt eine geprüfte Position zum Thema "
            f"{briefing.topic} ein. Begründung: {reason}."
        ),
    )


def _persona_policy(briefing: NegotiationTurnBriefing) -> tuple[str, str]:
    """Derive a stance from the persona card, not from an actor hash.

    The primary interest's weight is the mandate strength: a 1.0 priority supports, a 0.9
    priority with a veto right is conditional, a slightly weaker priority qualifies. Every
    branch names the card fact that caused it so the argument survives the jury question.
    """
    weights = briefing.interest_weights
    primary = weights[0] if weights else 0.0
    interest = briefing.interests[0] if briefing.interests else "no declared interest"
    veto = briefing.veto_classes[0] if briefing.veto_classes else ""
    constraint = briefing.constraints[0] if briefing.constraints else ""
    if primary >= 1.0:
        return "support", f"priority interest '{interest}' has weight {primary:.2f}"
    if primary >= 0.9 and veto:
        return (
            "conditional_accept",
            f"veto right over {veto}; priority interest '{interest}' has weight {primary:.2f}",
        )
    if primary >= 0.9:
        return "qualify", f"priority interest '{interest}' has weight {primary:.2f}"
    if constraint:
        return "qualify", f"constraint '{constraint}'; priority weight {primary:.2f}"
    return "oppose", f"no priority above 0.90 on '{interest}' (weight {primary:.2f})"
