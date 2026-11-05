"""Contract freeze: unverifiable claims remain visible (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names

from claim_validation.application.dto import ClaimDetailResult
from claim_validation.domain.events import ClaimMarkedUnverifiable


def test_unverifiable_event_names_the_claim_and_type() -> None:
    assert field_names(ClaimMarkedUnverifiable) == ["claim_id", "claim_type"]


def test_detail_result_always_carries_a_verdict() -> None:
    assert field_names(ClaimDetailResult) == [
        "claim_id",
        "text",
        "claim_type",
        "verdict",
        "path",
        "sources",
        "review_verdict",
        "review_basis",
    ]
