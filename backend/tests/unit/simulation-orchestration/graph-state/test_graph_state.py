"""Contract freeze: graph state (issue #205)."""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Any, cast

from tests.unit.simulation_orchestration_contract_helpers import enum_values, field_names

from simulation_orchestration.application.values import GraphState, RunPhase


def test_graph_state_contains_only_sequencing_facts() -> None:
    assert field_names(GraphState) == ["run_id", "round", "phase", "next_actor", "budget_used"]


def test_graph_state_never_contains_positions_arguments_or_evidence() -> None:
    forbidden = {"position", "argument", "evidence", "prompt", "persona", "text", "claim"}
    assert forbidden.isdisjoint(field_names(GraphState))


def test_graph_state_is_frozen() -> None:
    assert dataclasses.is_dataclass(GraphState)
    assert cast(Any, GraphState).__dataclass_params__.frozen is True


def test_phase_vocabulary_is_frozen() -> None:
    assert enum_values(RunPhase) == {"mandate", "select", "open", "rounds", "close", "done"}


# --- behaviour: pure state transitions (issue #207) -----------------------------------------

import pytest  # noqa: E402

from simulation_orchestration.application.state import (  # noqa: E402
    advance_phase,
    advance_round,
    initial_state,
    record_budget,
)
from simulation_orchestration.application.values import BudgetUsage, RunId  # noqa: E402


def test_initial_state_starts_at_mandate_with_zero_budget() -> None:
    state = initial_state(RunId("run_1"))

    assert state.phase is RunPhase.MANDATE
    assert state.round == 0
    assert state.budget_used == BudgetUsage()
    assert state.next_actor is None


def test_phase_transitions_are_pure_and_forward_only() -> None:
    state = initial_state(RunId("run_1"))

    advanced = advance_phase(state, RunPhase.OPEN, next_actor="oegk")

    assert advanced.phase is RunPhase.OPEN
    assert advanced.next_actor == "oegk"
    assert state.phase is RunPhase.MANDATE
    with pytest.raises(ValueError, match="cannot regress"):
        advance_phase(advanced, RunPhase.SELECT)


def test_rounds_advance_only_in_the_rounds_phase_without_mutating_state() -> None:
    state = advance_phase(initial_state(RunId("run_1")), RunPhase.ROUNDS)

    next_round = advance_round(state, next_actor="bmsgpk")

    assert next_round.round == 1
    assert next_round.next_actor == "bmsgpk"
    assert state.round == 0
    with pytest.raises(ValueError, match="rounds phase"):
        advance_round(initial_state(RunId("run_1")), next_actor=None)


def test_budget_snapshot_is_replaced_not_mutated() -> None:
    state = initial_state(RunId("run_1"))
    usage = BudgetUsage(invocations=2, tokens=120, cost=Decimal("0.12"))

    updated = record_budget(state, usage)

    assert updated.budget_used == usage
    assert state.budget_used == BudgetUsage()
