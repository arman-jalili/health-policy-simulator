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
