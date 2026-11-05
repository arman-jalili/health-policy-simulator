"""Contract freeze: the Claim aggregate surface (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names, method_names

from claim_validation.domain.claim import Claim
from claim_validation.domain.values import ClaimType


def test_claim_fields_are_frozen() -> None:
    assert field_names(Claim) == [
        "id",
        "text",
        "type",
        "measure",
        "verdict",
        "verification",
        "review",
        "events",
    ]


def test_claim_exposes_only_guarded_transitions() -> None:
    assert {
        "verify",
        "mark_unsupported",
        "escalate",
        "resolve_review",
        "drain_events",
    } <= method_names(Claim)


def test_claim_is_typed_and_identity_based() -> None:
    claim = Claim(id="clm_1", text="3,2 Mrd. Euro", type=ClaimType.QUANTITATIVE)  # type: ignore[arg-type]

    assert claim.id == "clm_1"
    assert claim.type is ClaimType.QUANTITATIVE
    assert claim.verdict.value == "pending"
