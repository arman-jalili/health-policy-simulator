"""Contract freeze: budget guard (issue #205)."""

from __future__ import annotations

from tests.unit.simulation_orchestration_contract_helpers import (
    enum_values,
    field_names,
    parameter_names,
)

from simulation_orchestration.application.errors import RunBudgetExceeded
from simulation_orchestration.application.events import RunBudgetExhausted
from simulation_orchestration.application.rules import BudgetGuard
from simulation_orchestration.application.values import (
    BudgetDecision,
    BudgetDimension,
    BudgetUsage,
    RunBudget,
)


def test_budget_values_are_frozen() -> None:
    assert field_names(RunBudget) == ["max_invocations", "max_tokens", "max_cost"]
    assert field_names(BudgetUsage) == ["invocations", "tokens", "cost"]
    assert field_names(BudgetDecision) == ["allowed", "dimension", "limit", "used", "reason"]


def test_budget_dimensions_are_frozen() -> None:
    assert enum_values(BudgetDimension) == {"invocations", "tokens", "cost"}


def test_guard_runs_before_the_call() -> None:
    assert parameter_names(BudgetGuard.evaluate) == [
        "self",
        "budget",
        "usage",
        "requested_tokens",
        "requested_cost",
    ]


def test_exhaustion_event_and_error_are_frozen() -> None:
    assert RunBudgetExhausted.name == "RunBudgetExhausted"
    assert field_names(RunBudgetExhausted) == ["run_id", "dimension", "limit", "used"]
    assert RunBudgetExceeded.code == "RUN_BUDGET_EXHAUSTED"
