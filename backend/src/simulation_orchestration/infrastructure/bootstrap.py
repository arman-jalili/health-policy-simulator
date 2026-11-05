"""Temporary deterministic graph used until NegotiationSession lands (issues #216, #237)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from shared.ids import new_id
from simulation_orchestration.application.commands import RecordAgentInvocationRequest
from simulation_orchestration.application.services import RecordAgentInvocation
from simulation_orchestration.application.values import (
    GraphState,
    InvocationId,
    InvocationOutcome,
    PromptRef,
    RunPhase,
)


class _BootstrapNode:
    """One deterministic scripted turn; every turn is metered like a real provider call."""

    phase: RunPhase
    name: str

    def __init__(self, recorder: RecordAgentInvocation, *, model: str) -> None:
        self._recorder = recorder
        self._model = model

    async def execute(self, state: GraphState) -> GraphState:
        await self._recorder.execute(
            RecordAgentInvocationRequest(
                invocation_id=InvocationId(new_id("inv")),
                run_id=state.run_id,
                round=state.round,
                stakeholder="bootstrap",
                purpose="bootstrap_turn",
                model=self._model,
                prompt=PromptRef("bootstrap-turn", 1),
                parameters={"deterministic": True},
                evidence_pack_ids=(),
                input_tokens=1,
                output_tokens=1,
                cost_estimate=Decimal("0"),
                latency_ms=0,
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
