"""Contract freeze: unsupported claims are surfaced, not dropped (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names

from claim_validation.application.dto import ClaimDetailResult, ClaimVerdictResult
from claim_validation.domain.events import UnsupportedAssertionFlagged


def test_unsupported_event_records_reason() -> None:
    assert field_names(UnsupportedAssertionFlagged) == ["claim_id", "reason"]


def test_results_carry_verdict_and_claim_identity() -> None:
    assert field_names(ClaimVerdictResult) == [
        "claim_id",
        "verdict",
        "path",
        "claim_type",
        "sources",
        "delta",
    ]
    assert "verdict" in field_names(ClaimDetailResult)
