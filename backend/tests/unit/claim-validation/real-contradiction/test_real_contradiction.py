"""Contract freeze: contradiction findings and detector (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names, parameter_names

from claim_validation.domain.entities import ContradictionFinding
from claim_validation.domain.events import ContradictionDetected
from claim_validation.domain.services import ContradictionDetector


def test_finding_links_two_claims_with_delta() -> None:
    assert field_names(ContradictionFinding) == [
        "id",
        "claim_id_a",
        "claim_id_b",
        "measure",
        "delta",
    ]
    assert field_names(ContradictionDetected) == [
        "claim_id_a",
        "claim_id_b",
        "measure",
        "delta",
    ]


def test_detector_requires_both_values_and_the_band() -> None:
    assert parameter_names(ContradictionDetector.is_contradiction) == [
        "self",
        "a",
        "b",
        "band",
    ]
