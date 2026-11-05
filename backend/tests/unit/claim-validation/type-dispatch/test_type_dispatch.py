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
