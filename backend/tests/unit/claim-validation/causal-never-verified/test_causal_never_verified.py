"""Contract freeze: causal appraisal is constrained (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names, parameter_names

from claim_validation.domain.events import CausalClaimAppraised
from claim_validation.domain.services import CausalAppraiser
from claim_validation.domain.values import CausalSupport, VerificationVerdict


def test_causal_support_has_no_verified_member() -> None:
    assert {member.value for member in CausalSupport} == {
        "supported",
        "contested",
        "unaddressed",
    }
    assert VerificationVerdict.VERIFIED.value == "verified"


def test_appraisal_event_and_service_are_frozen() -> None:
    assert field_names(CausalClaimAppraised) == ["claim_id", "support", "study_ids"]
    assert parameter_names(CausalAppraiser.appraise) == ["self", "support"]
