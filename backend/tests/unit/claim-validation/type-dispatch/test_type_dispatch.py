"""Contract freeze: type-directed verification paths (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import parameter_names

from claim_validation.domain.errors import PathNotApplicable
from claim_validation.domain.services import path_for
from claim_validation.domain.values import VerificationPath


def test_path_selector_is_a_function_of_claim_type() -> None:
    assert parameter_names(path_for) == ["claim_type"]
    error = PathNotApplicable("clm_1", "causal", "quantitative")
    assert error.code == "PATH_NOT_APPLICABLE"
    assert error.status_code == 422


def test_path_vocabulary_matches_claim_vocabulary() -> None:
    assert {member.value for member in VerificationPath} == {
        "quantitative",
        "legal",
        "causal",
        "qualitative",
    }


# --- behaviour: one legal path per claim type (issue #168) -----------------------------------

import pytest  # noqa: E402

from claim_validation.domain.claim import Claim  # noqa: E402
from claim_validation.domain.values import ClaimId, ClaimType, VerificationEvidence  # noqa: E402

_EXPECTED = {
    ClaimType.QUANTITATIVE: VerificationPath.QUANTITATIVE,
    ClaimType.LEGAL: VerificationPath.LEGAL,
    ClaimType.CAUSAL: VerificationPath.CAUSAL,
    ClaimType.QUALITATIVE: VerificationPath.QUALITATIVE,
}


@pytest.mark.parametrize(("claim_type", "expected"), _EXPECTED.items())
def test_path_selector_maps_every_type(claim_type: ClaimType, expected: VerificationPath) -> None:
    assert path_for(claim_type) is expected


_WRONG = [
    (claim_type, path)
    for claim_type, legal in _EXPECTED.items()
    for path in _EXPECTED.values()
    if path is not legal
]


@pytest.mark.parametrize(("claim_type", "wrong_path"), _WRONG)
def test_every_wrong_path_is_refused_before_any_state_change(
    claim_type: ClaimType,
    wrong_path: VerificationPath,
) -> None:
    claim = Claim(id=ClaimId("clm_dispatch"), text="x", type=claim_type)

    with pytest.raises(PathNotApplicable):
        claim.verify(wrong_path, VerificationEvidence())

    assert claim.verdict.value == "pending"
    assert claim.verification is None
    assert claim.events == []
