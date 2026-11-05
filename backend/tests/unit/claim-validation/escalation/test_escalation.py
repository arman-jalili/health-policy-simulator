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
