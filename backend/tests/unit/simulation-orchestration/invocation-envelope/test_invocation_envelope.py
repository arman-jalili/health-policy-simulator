"""Contract freeze: invocation envelope (issue #205)."""

from __future__ import annotations

from tests.unit.simulation_orchestration_contract_helpers import field_names, parameter_names

from simulation_orchestration.application.commands import RecordAgentInvocationRequest
from simulation_orchestration.application.dto import InvocationEnvelope, InvocationRecordResult
from simulation_orchestration.application.services import RecordAgentInvocation
from simulation_orchestration.application.values import InvocationOutcome, PromptRef


def test_envelope_has_the_full_reproducibility_fields() -> None:
    assert field_names(InvocationEnvelope) == [
        "invocation_id",
        "run_id",
        "round",
        "stakeholder",
        "purpose",
        "model",
        "prompt",
        "parameters",
        "evidence_pack_ids",
        "input_tokens",
        "output_tokens",
        "cost_estimate",
        "latency_ms",
        "outcome",
        "created_at",
    ]
    assert field_names(RecordAgentInvocationRequest)[:15] == field_names(InvocationEnvelope)[:14]


def test_prompt_identity_is_name_at_version() -> None:
    assert PromptRef("policy", 3).identity == "policy@3"


def test_record_service_is_frozen() -> None:
    assert parameter_names(RecordAgentInvocation.__init__) == [
        "self",
        "invocations",
        "prices",
        "clock",
    ]
    assert field_names(InvocationRecordResult) == [
        "invocation_id",
        "run_id",
        "prompt",
        "cost_estimate",
    ]


def test_invocation_outcomes_are_frozen() -> None:
    assert {item.value for item in InvocationOutcome} == {
        "success",
        "failed",
        "budget_rejected",
    }


# --- behaviour: exactly one metered envelope per call (issue #208) --------------------------

from dataclasses import replace  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

from simulation_orchestration.application.errors import UnknownModel  # noqa: E402
from simulation_orchestration.application.values import (  # noqa: E402
    InvocationId,
    ModelPrice,
    RunId,
)
from simulation_orchestration.infrastructure.memory import (  # noqa: E402
    InMemoryInvocationStore,
)
from simulation_orchestration.infrastructure.pricing import StaticPriceTable  # noqa: E402


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


def _service() -> tuple[RecordAgentInvocation, InMemoryInvocationStore]:
    store = InMemoryInvocationStore()
    prices = StaticPriceTable(
        {
            "model-a": ModelPrice("model-a", Decimal("0.002"), Decimal("0.004")),
        }
    )
    return RecordAgentInvocation(invocations=store, prices=prices, clock=_Clock()), store


def _request(invocation_id: str = "inv_1") -> RecordAgentInvocationRequest:
    return RecordAgentInvocationRequest(
        invocation_id=InvocationId(invocation_id),
        run_id=RunId("run_1"),
        round=2,
        stakeholder="oegk",
        purpose="take_turn",
        model="model-a",
        prompt=PromptRef("take-turn", 3),
        parameters={"temperature": 0},
        evidence_pack_ids=("pack_1",),
        input_tokens=1000,
        output_tokens=500,
        cost_estimate=Decimal("999"),
        latency_ms=42,
    )


async def test_every_call_writes_one_envelope_with_model_prompt_tokens_and_cost() -> None:
    service, store = _service()

    result = await service.execute(_request())

    envelopes = await store.list_for_run(RunId("run_1"))
    assert len(envelopes) == 1
    envelope = envelopes[0]
    assert envelope.model == "model-a"
    assert envelope.prompt.identity == "take-turn@3"
    assert envelope.input_tokens == 1000
    assert envelope.output_tokens == 500
    assert envelope.cost_estimate == Decimal("0.004")
    assert envelope.outcome is InvocationOutcome.SUCCESS
    assert result.cost_estimate == Decimal("0.004")


async def test_duplicate_invocation_id_does_not_write_a_second_row() -> None:
    service, store = _service()

    await service.execute(_request())
    await service.execute(_request())

    assert len(await store.list_for_run(RunId("run_1"))) == 1


async def test_usage_aggregates_per_stakeholder_and_round() -> None:
    service, store = _service()

    await service.execute(_request("inv_1"))
    await service.execute(_request("inv_2"))

    usage = await store.usage_for_run(RunId("run_1"))
    assert usage.invocations == 2
    assert usage.input_tokens == 2000
    assert usage.output_tokens == 1000
    assert usage.by_stakeholder[0].stakeholder == "oegk"
    assert usage.by_round[0].round == 2


async def test_unknown_model_fails_closed() -> None:
    service, _ = _service()

    with pytest.raises(UnknownModel, match="no price entry"):
        await service.execute(replace(_request(), model="unknown"))
