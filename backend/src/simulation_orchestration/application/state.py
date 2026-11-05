"""Graph-state construction and pure transitions (issue #207).

Canonical: .pi/architecture/modules/simulation-orchestration.md

The state is a sequencing record: ids, round, phase, next actor and budget usage. Positions,
arguments, evidence and prompts are rejected by construction because they are not fields here.
All helpers return a new frozen value; callers cannot mutate the prior state.
"""

from __future__ import annotations

from dataclasses import replace

from simulation_orchestration.application.values import (
    BudgetUsage,
    GraphState,
    RunId,
    RunPhase,
)

_PHASE_ORDER = {
    RunPhase.MANDATE: 0,
    RunPhase.SELECT: 1,
    RunPhase.OPEN: 2,
    RunPhase.ROUNDS: 3,
    RunPhase.CLOSE: 4,
    RunPhase.DONE: 5,
}


def initial_state(run_id: RunId) -> GraphState:
    """Start a run at the mandate phase with a zeroed budget."""
    return GraphState(
        run_id=run_id,
        round=0,
        phase=RunPhase.MANDATE,
        next_actor=None,
        budget_used=BudgetUsage(),
    )


def advance_phase(
    state: GraphState, phase: RunPhase, *, next_actor: str | None = None
) -> GraphState:
    """Move forward in the phase machine; regression is rejected."""
    if _PHASE_ORDER[phase] < _PHASE_ORDER[state.phase]:
        raise ValueError(f"phase cannot regress from {state.phase} to {phase}")
    return replace(state, phase=phase, next_actor=next_actor)


def advance_round(state: GraphState, *, next_actor: str | None) -> GraphState:
    """Start the next round without changing the phase or budget."""
    if state.phase is not RunPhase.ROUNDS:
        raise ValueError("rounds can only advance in the rounds phase")
    return replace(state, round=state.round + 1, next_actor=next_actor)


def record_budget(state: GraphState, usage: BudgetUsage) -> GraphState:
    """Replace the budget snapshot; callers pass the authoritative cumulative usage."""
    return replace(state, budget_used=usage)
