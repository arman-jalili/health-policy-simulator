"""Bootstrap graph used until NegotiationSession lands (issue #216)."""

from __future__ import annotations

from dataclasses import replace

from simulation_orchestration.application.values import GraphState, RunPhase


class BootstrapTurnNode:
    """One deterministic turn that closes the run, proving worker/progress wiring."""

    name = "bootstrap-turn"
    phase = RunPhase.MANDATE

    async def execute(self, state: GraphState) -> GraphState:
        return replace(state, phase=RunPhase.DONE, round=state.round + 1, next_actor=None)
