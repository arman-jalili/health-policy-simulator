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


# --- behaviour: appraisal is constrained and never settles as verified (issue #169) ----------

import pytest  # noqa: E402

from claim_validation.domain.claim import Claim  # noqa: E402
from claim_validation.domain.events import ClaimVerified  # noqa: E402
from claim_validation.domain.values import (  # noqa: E402
    ClaimId,
    ClaimType,
    VerificationEvidence,
    VerificationPath,
)


@pytest.mark.parametrize(
    "support",
    [CausalSupport.SUPPORTED, CausalSupport.CONTESTED, CausalSupport.UNADDRESSED],
)
def test_causal_claim_never_emits_verified(support: CausalSupport) -> None:
    claim = Claim(id=ClaimId("clm_causal"), text="Weil X, sinkt Y", type=ClaimType.CAUSAL)

    claim.verify(
        VerificationPath.CAUSAL,
        VerificationEvidence(support=support, study_ids=("study_1", "study_2")),
    )

    assert claim.verdict is not VerificationVerdict.VERIFIED
    assert not any(isinstance(event, ClaimVerified) for event in claim.events)
    event = claim.events[0]
    assert isinstance(event, CausalClaimAppraised)
    assert event.study_ids == ("study_1", "study_2")


def test_missing_causal_support_defaults_to_unaddressed() -> None:
    assert CausalAppraiser().appraise(None) is CausalSupport.UNADDRESSED
