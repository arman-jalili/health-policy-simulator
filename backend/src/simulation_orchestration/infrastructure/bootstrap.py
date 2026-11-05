"""Temporary deterministic graph used until NegotiationSession lands (issues #216, #237)."""

from __future__ import annotations

import hashlib
import time
from dataclasses import replace
from decimal import Decimal

from simulation_orchestration.application.commands import RecordAgentInvocationRequest
from simulation_orchestration.application.ports import LLMClient
from simulation_orchestration.application.services import RecordAgentInvocation
from simulation_orchestration.application.values import (
    GraphState,
    InvocationId,
    InvocationOutcome,
    LLMRequest,
    PromptRef,
    RunPhase,
)


class _BootstrapNode:
    """One deterministic scripted turn; every turn is metered like a real provider call."""

    phase: RunPhase
    name: str

    def __init__(self, recorder: RecordAgentInvocation, *, model: str, llm: LLMClient) -> None:
        self._recorder = recorder
        self._model = model
        self._llm = llm

    def _invocation_id(self, state: GraphState) -> InvocationId:
        material = f"{state.run_id}|{state.round}|bootstrap|{self.name}"
        return InvocationId("inv_" + hashlib.sha256(material.encode()).hexdigest()[:26])

    async def execute(self, state: GraphState) -> GraphState:
        prompt = f"bootstrap turn {state.run_id} round {state.round} node {self.name}"
        prompt_ref = PromptRef("bootstrap-turn", 1)
        started = time.perf_counter()
        response = await self._llm.complete(
            LLMRequest(
                model=self._model,
                prompt=prompt,
                prompt_ref=prompt_ref,
                parameters={"synthetic": True},
            )
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        await self._recorder.execute(
            RecordAgentInvocationRequest(
                invocation_id=self._invocation_id(state),
                run_id=state.run_id,
                round=state.round,
                stakeholder="bootstrap",
                purpose="bootstrap_turn",
                model=response.model,
                prompt=prompt_ref,
                parameters={"synthetic": True},
                evidence_pack_ids=(),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_estimate=Decimal("0"),
                latency_ms=latency_ms,
                outcome=InvocationOutcome.SUCCESS,
            )
        )
        return replace(state, phase=RunPhase.DONE, round=state.round + 1, next_actor=None)


class BootstrapMandateNode(_BootstrapNode):
    name = "bootstrap-mandate"
    phase = RunPhase.MANDATE

    async def execute(self, state: GraphState) -> GraphState:
        metered = await super().execute(state)
        return replace(metered, phase=RunPhase.ROUNDS)


class BootstrapRoundNode(_BootstrapNode):
    name = "bootstrap-round"
    phase = RunPhase.ROUNDS
