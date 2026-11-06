"""Contract freeze: evidence requirement (issue #282, implements #290)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    field_names,
    parameter_names,
)

from negotiation_session.application.services import TakeNegotiationTurn
from negotiation_session.domain.entities import Argument
from negotiation_session.domain.errors import ArgumentWithoutEvidence, ClaimVerdictRejected
from negotiation_session.domain.events import ArgumentSubmitted
from negotiation_session.domain.values import ClaimEvidence, ClaimStatement


def test_argument_carries_evidence_or_an_unsupported_flag() -> None:
    assert field_names(Argument)[6:] == [
        "evidence",
        "unsupported",
        "round_number",
        "invocation_id",
    ]
    assert parameter_names(Argument.new) == [
        "argument_id",
        "stakeholder",
        "target",
        "stance",
        "text",
        "claims",
        "evidence",
        "unsupported",
        "round_number",
        "invocation_id",
    ]


def test_evidence_is_the_acl_target_not_a_retrieval_hit() -> None:
    assert field_names(ClaimEvidence) == ["evidence_id", "passage_id", "stance", "provenance"]
    assert field_names(ClaimStatement) == ["text", "claim_id", "verdict"]


def test_every_argument_is_auditable_with_its_invocation() -> None:
    assert field_names(ArgumentSubmitted) == [
        "run_id",
        "round",
        "argument_id",
        "stakeholder_id",
        "target",
        "stance",
        "evidence_ids",
        "invocation_id",
    ]
    assert parameter_names(TakeNegotiationTurn.execute) == ["self", "request"]


def test_evidence_errors_have_stable_codes() -> None:
    assert ArgumentWithoutEvidence.code == "ARGUMENT_WITHOUT_EVIDENCE"
    assert ClaimVerdictRejected.code == "CLAIM_VERDICT_REJECTED"
