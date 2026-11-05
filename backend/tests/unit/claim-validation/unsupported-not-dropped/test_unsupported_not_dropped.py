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


# --- behaviour: unsupported claims stay queryable (issue #175) ------------------------------

from claim_validation.domain.claim import Claim  # noqa: E402
from claim_validation.domain.values import (  # noqa: E402
    ClaimId,
    ClaimType,
    VerificationEvidence,
    VerificationPath,
    VerificationVerdict,
)


def test_legal_claim_without_evidence_becomes_unsupported() -> None:
    claim = Claim(id=ClaimId("clm_unsup"), text="Das ist gesetzlich verboten", type=ClaimType.LEGAL)

    claim.verify(VerificationPath.LEGAL, VerificationEvidence())

    assert claim.verdict is VerificationVerdict.UNSUPPORTED
    assert claim.verification is not None
    assert claim.verification.path is VerificationPath.LEGAL
    assert any(
        getattr(event, "reason", "") == "no provision above threshold" for event in claim.events
    )


def test_unsupported_claim_is_not_marked_verified_or_dropped() -> None:
    claim = Claim(id=ClaimId("clm_unsup2"), text="Eine Behauptung", type=ClaimType.LEGAL)

    claim.verify(VerificationPath.LEGAL, VerificationEvidence())

    assert claim.verdict is not VerificationVerdict.VERIFIED
    assert claim.id == "clm_unsup2"
    assert claim.text == "Eine Behauptung"
