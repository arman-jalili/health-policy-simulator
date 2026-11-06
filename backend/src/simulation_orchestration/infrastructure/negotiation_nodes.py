"""Graph nodes that drive a real NegotiationSession run (issue #415)."""

from __future__ import annotations

import hashlib
import time
from dataclasses import replace
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
        prompt = (
            f"You are institutional stakeholder {actor} in round {state.round}. "
            "Write one concise argumentative turn for the negotiation. "
            "Name no natural person and quote no one."
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
                parameters={"synthetic": self._synthetic},
                evidence_pack_ids=(),
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
                text=response.text,
            )
        )
        view = await self._negotiation.load_state(state.run_id)
        if view.terminal:
            return replace(state, phase=RunPhase.DONE, round=view.round, next_actor=None)
        if view.next_actor is None:
            raise RuntimeError(f"run {state.run_id} is open but has no next actor")
        return replace(state, round=view.round, next_actor=view.next_actor)
