"""Graph nodes that drive a real NegotiationSession run (issue #415)."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, replace
from decimal import Decimal

from simulation_orchestration.application.commands import RecordAgentInvocationRequest
from simulation_orchestration.application.ports import LLMClient, NegotiationGateway
from simulation_orchestration.application.services import RecordAgentInvocation
from simulation_orchestration.application.values import (
    GraphState,
    InvocationId,
    InvocationOutcome,
    LLMRequest,
    NegotiationTurnCommand,
    PromptRef,
    RunPhase,
)

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
    ) -> None:
        self._recorder = recorder
        self._negotiation = negotiation
        self._llm = llm
        self._model = model
        self._synthetic = synthetic

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
            f"Current stances: {briefing.current_stances or 'none'}.\n"
            f"Previous learning: {briefing.previous_learning or 'none'}.\n"
            "Write one institutional argument. Return JSON only with keys "
            '"stance" (support|oppose|qualify|conditional_accept), '
            '"proposal" (short string), "claims" (array of strings), and "argument" (string). '
            "Do not name or quote a natural person."
        )
        started = time.perf_counter()
        response = await self._llm.complete(
            LLMRequest(
                model=self._model,
                prompt=prompt,
                prompt_ref=_PROMPT,
                parameters={"synthetic": self._synthetic},
            )
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        decision = _decision(response.text, actor)
        invocation_id = InvocationId(
            "inv_"
            + hashlib.sha256(
                f"{state.run_id}|{state.round}|{actor}|stakeholder-turn".encode()
            ).hexdigest()[:26]
        )
        await self._recorder.execute(
            RecordAgentInvocationRequest(
                invocation_id=invocation_id,
                run_id=state.run_id,
                round=state.round,
                stakeholder=actor,
                purpose="stakeholder_turn",
                model=response.model,
                prompt=_PROMPT,
                parameters={"synthetic": self._synthetic, "topic": briefing.topic},
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


def _decision(text: str, actor: str) -> _Decision:
    """Parse the model's JSON decision; scripted/non-JSON output gets a deterministic stance."""
    payload = text.strip()
    if payload.startswith("```"):
        lines = payload.splitlines()
        payload = "\n".join(lines[1:-1] if len(lines) > 2 else lines[1:])
    try:
        parsed = json.loads(payload)
    except (TypeError, ValueError):
        parsed = {}
    stance = str(parsed.get("stance") or "").strip().lower()
    if stance not in {"support", "oppose", "qualify", "conditional_accept"}:
        stance = _fallback_stance(actor)
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
        argument=str(parsed.get("argument") or parsed.get("text") or text),
    )


def _fallback_stance(actor: str) -> str:
    options = ("support", "oppose", "qualify", "conditional_accept")
    index = int(hashlib.sha256(actor.encode()).hexdigest(), 16) % len(options)
    return options[index]
