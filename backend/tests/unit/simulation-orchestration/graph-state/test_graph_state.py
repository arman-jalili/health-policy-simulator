"""Contract freeze: graph state (issue #205)."""

from __future__ import annotations

import dataclasses
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
