"""Progress payloads must survive a JSON column: Decimal cost is the first paid-call case."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from simulation_orchestration.application.events import AgentInvocationRecorded, RunBudgetExhausted
from simulation_orchestration.application.progress import ProgressPublisher
from simulation_orchestration.application.values import (
    BudgetDimension,
    InvocationId,
    ProgressKind,
    PromptRef,
    RunId,
)
from simulation_orchestration.infrastructure.memory import InMemoryProgressStore


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


async def test_invocation_cost_is_persisted_as_a_json_value() -> None:
    store = InMemoryProgressStore()
    publisher = ProgressPublisher(store, _Clock())

    event = AgentInvocationRecorded(
        run_id=RunId("run_1"),
        invocation_id=InvocationId("inv_1"),
        prompt=PromptRef("stakeholder-turn", 1),
        cost_estimate=Decimal("0.129"),
    )
    view = await publisher.publish(RunId("run_1"), ProgressKind.INVOCATION_RECORDED, event)

    json.dumps(dict(view.payload))  # a Decimal here would raise TypeError
    assert view.payload["cost_estimate"] == "0.129"


async def test_budget_decimals_are_persisted_as_strings() -> None:
    store = InMemoryProgressStore()
    publisher = ProgressPublisher(store, _Clock())

    event = RunBudgetExhausted(
        run_id=RunId("run_1"),
        dimension=BudgetDimension.COST,
        limit=Decimal("0.50"),
        used=Decimal("0.51"),
    )
    view = await publisher.publish(RunId("run_1"), ProgressKind.BUDGET_EXHAUSTED, event)

    json.dumps(dict(view.payload))
    assert (view.payload["limit"], view.payload["used"]) == ("0.50", "0.51")
