"""Contract freeze: expert review lifecycle (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names, method_names

from claim_validation.application.commands import ResolveExpertReviewRequest
from claim_validation.domain.claim import Claim
from claim_validation.domain.entities import ExpertReview
from claim_validation.domain.errors import ReviewNotEscalated
from claim_validation.domain.events import ExpertReviewResolved


def test_review_entities_and_events_are_frozen() -> None:
    assert field_names(ExpertReview) == ["id", "question", "verdict", "basis"]
    assert field_names(ExpertReviewResolved) == ["claim_id", "verdict", "basis"]
    assert field_names(ResolveExpertReviewRequest) == ["claim_id", "verdict", "basis"]


def test_claim_review_transition_is_guarded() -> None:
    assert {"escalate", "resolve_review"} <= method_names(Claim)
    assert ReviewNotEscalated.code == "REVIEW_NOT_ESCALATED"


# --- behaviour: ambiguity only settles through review (issue #174) ---------------------------

import pytest  # noqa: E402

from claim_validation.domain.claim import Claim as _Claim  # noqa: E402
from claim_validation.domain.events import ClaimEscalatedForReview  # noqa: E402
from claim_validation.domain.values import (  # noqa: E402
    ClaimId,
    ClaimType,
    VerificationVerdict,
)


def test_escalation_records_a_review_and_stays_ambiguous() -> None:
    claim = _Claim(id=ClaimId("clm_esc"), text="3,2 Mrd", type=ClaimType.QUANTITATIVE)

    claim.escalate("which reference applies?")

    assert claim.verdict is VerificationVerdict.AMBIGUOUS
    assert claim.review is not None
    assert claim.review.question == "which reference applies?"
    assert claim.review.verdict is VerificationVerdict.PENDING
    assert isinstance(claim.events[0], ClaimEscalatedForReview)


def test_review_cannot_set_unsupported_or_pending() -> None:
    claim = _Claim(id=ClaimId("clm_esc2"), text="3,2 Mrd", type=ClaimType.QUANTITATIVE)
    claim.escalate("which reference applies?")

    with pytest.raises(ReviewNotEscalated, match="verified or contradicted"):
        claim.resolve_review(VerificationVerdict.UNSUPPORTED, "not a review verdict")

    assert claim.verdict is VerificationVerdict.AMBIGUOUS
    assert claim.review is not None
    assert claim.review.verdict is VerificationVerdict.PENDING


def test_review_resolution_records_basis_and_event() -> None:
    claim = _Claim(id=ClaimId("clm_esc3"), text="3,2 Mrd", type=ClaimType.QUANTITATIVE)
    claim.escalate("which reference applies?")

    claim.resolve_review(VerificationVerdict.CONTRADICTED, "ministry correction")

    assert claim.verdict is VerificationVerdict.CONTRADICTED
    assert claim.review is not None
    assert claim.review.basis == "ministry correction"
    assert isinstance(claim.events[-1], ExpertReviewResolved)
