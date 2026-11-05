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


# --- behaviour: pre-call guard and exhaustion event (issue #209) ----------------------------

from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

from simulation_orchestration.application.values import RunId  # noqa: E402


def _usage(invocations: int = 0, tokens: int = 0, cost: str = "0") -> BudgetUsage:
    return BudgetUsage(invocations=invocations, tokens=tokens, cost=Decimal(cost))


def test_under_budget_is_allowed() -> None:
    decision = BudgetGuard().evaluate(
        budget=RunBudget(max_invocations=5, max_tokens=1000, max_cost=Decimal("1")),
        usage=_usage(invocations=1, tokens=100, cost="0.10"),
        requested_tokens=200,
        requested_cost=Decimal("0.20"),
    )

    assert decision.allowed is True
    assert decision.dimension is None


def test_exact_limit_is_allowed() -> None:
    decision = BudgetGuard().evaluate(
        budget=RunBudget(max_cost=Decimal("0.30")),
        usage=_usage(cost="0.10"),
        requested_tokens=0,
        requested_cost=Decimal("0.20"),
    )

    assert decision.allowed is True


def test_each_dimension_rejects_before_the_call() -> None:
    guard = BudgetGuard()

    invocations = guard.evaluate(
        budget=RunBudget(max_invocations=1),
        usage=_usage(invocations=1),
        requested_tokens=0,
        requested_cost=Decimal("0"),
    )
    tokens = guard.evaluate(
        budget=RunBudget(max_tokens=100),
        usage=_usage(tokens=80),
        requested_tokens=21,
        requested_cost=Decimal("0"),
    )
    cost = guard.evaluate(
        budget=RunBudget(max_cost=Decimal("0.25")),
        usage=_usage(cost="0.20"),
        requested_tokens=0,
        requested_cost=Decimal("0.06"),
    )

    assert (invocations.allowed, invocations.dimension) == (False, BudgetDimension.INVOCATIONS)
    assert (tokens.allowed, tokens.dimension) == (False, BudgetDimension.TOKENS)
    assert (cost.allowed, cost.dimension) == (False, BudgetDimension.COST)
    assert cost.limit == Decimal("0.25")
    assert cost.used == Decimal("0.26")


def test_unset_dimensions_are_unbounded() -> None:
    assert (
        BudgetGuard()
        .evaluate(
            budget=RunBudget(),
            usage=_usage(invocations=10_000, tokens=10_000_000, cost="1000"),
            requested_tokens=1_000_000,
            requested_cost=Decimal("100"),
        )
        .allowed
    )


def test_exhaustion_event_carries_the_breached_dimension() -> None:
    decision = BudgetGuard().evaluate(
        budget=RunBudget(max_cost=Decimal("0.25")),
        usage=_usage(cost="0.20"),
        requested_tokens=0,
        requested_cost=Decimal("0.06"),
    )

    event = BudgetGuard().exhaustion_event(RunId("run_1"), decision)

    assert event.dimension is BudgetDimension.COST
    assert event.limit == Decimal("0.25")
    assert event.used == Decimal("0.26")


def test_event_cannot_be_built_for_an_allowed_call() -> None:
    with pytest.raises(ValueError, match="rejected"):
        BudgetGuard().exhaustion_event(RunId("run_1"), BudgetDecision(allowed=True))


def test_negative_requests_are_rejected() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        BudgetGuard().evaluate(
            budget=RunBudget(),
            usage=_usage(),
            requested_tokens=-1,
            requested_cost=Decimal("0"),
        )
