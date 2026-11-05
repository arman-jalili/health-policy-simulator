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


# --- behaviour: aggregate transitions (issue #165) -------------------------------------------

from datetime import date  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

from claim_validation.domain.errors import PathNotApplicable, ReviewNotEscalated  # noqa: E402
from claim_validation.domain.events import (  # noqa: E402
    CausalClaimAppraised,
    ClaimMarkedUnverifiable,
    UnsupportedAssertionFlagged,
)
from claim_validation.domain.values import (  # noqa: E402
    CausalSupport,
    ClaimId,
    MeasureReference,
    ReferenceFigure,
    VerificationEvidence,
    VerificationPath,
    VerificationVerdict,
)
from evidence_corpus.domain.values import AuthorityTier  # noqa: E402


def _measure() -> MeasureReference:
    return MeasureReference("Kassenstellen", "count", "2026", "AT")


def _reference() -> ReferenceFigure:
    return ReferenceFigure(
        id="fig_1",  # type: ignore[arg-type]
        measure=_measure(),
        value=Decimal("3.2"),
        tier=AuthorityTier.OFFICIAL_STATISTICS,
        as_of=date(2026, 1, 1),
        source_id="src_1",
    )


def test_causal_claim_on_the_quantitative_path_is_refused() -> None:
    claim = Claim(id="clm_1", text="Weil X, sinkt Y", type=ClaimType.CAUSAL)  # type: ignore[arg-type]

    with pytest.raises(PathNotApplicable, match="not applicable"):
        claim.verify(VerificationPath.QUANTITATIVE, VerificationEvidence())


@pytest.mark.parametrize(
    "support",
    [CausalSupport.SUPPORTED, CausalSupport.CONTESTED, CausalSupport.UNADDRESSED],
)
def test_causal_appraisal_is_never_verified(support: CausalSupport) -> None:
    claim = Claim(id="clm_2", text="Weil X, sinkt Y", type=ClaimType.CAUSAL)  # type: ignore[arg-type]

    claim.verify(
        VerificationPath.CAUSAL,
        VerificationEvidence(support=support, study_ids=("study_1",)),
    )

    assert claim.verdict is VerificationVerdict.AMBIGUOUS
    assert claim.verdict.value != "verified"
    event = claim.events[0]
    assert isinstance(event, CausalClaimAppraised)
    assert event.support is support


def test_qualitative_claim_is_recorded_unverifiable_not_dropped() -> None:
    claim = Claim(id="clm_3", text="Die Stimmung ist angespannt", type=ClaimType.QUALITATIVE)  # type: ignore[arg-type]

    claim.verify(VerificationPath.QUALITATIVE, VerificationEvidence())

    assert claim.verdict is VerificationVerdict.AMBIGUOUS
    assert isinstance(claim.events[0], ClaimMarkedUnverifiable)
    assert claim.verification is not None
    assert claim.verification.path is VerificationPath.QUALITATIVE


def test_quantitative_claim_without_a_reference_escalates() -> None:
    claim = Claim(
        id=ClaimId("clm_4"),
        text="3,2 Mrd",
        type=ClaimType.QUANTITATIVE,
        measure=_measure(),
    )

    claim.verify(
        VerificationPath.QUANTITATIVE,
        VerificationEvidence(asserted_value=Decimal("3.2"), asserted_measure=_measure()),
    )

    assert claim.verdict is VerificationVerdict.AMBIGUOUS
    assert claim.review is not None


def test_escalated_claim_needs_review_before_it_settles() -> None:
    claim = Claim(
        id=ClaimId("clm_5"),
        text="3,2 Mrd",
        type=ClaimType.QUANTITATIVE,
        measure=_measure(),
    )
    claim.verify(
        VerificationPath.QUANTITATIVE,
        VerificationEvidence(asserted_value=Decimal("3.2"), asserted_measure=_measure()),
    )

    claim.resolve_review(VerificationVerdict.VERIFIED, "reference figure confirmed by ministry")

    assert claim.verdict is VerificationVerdict.VERIFIED
    assert claim.review is not None
    assert claim.review.basis.startswith("reference figure")


def test_unresolved_claim_cannot_be_reviewed() -> None:
    claim = Claim(id="clm_6", text="3,2 Mrd", type=ClaimType.QUANTITATIVE)  # type: ignore[arg-type]

    with pytest.raises(ReviewNotEscalated, match="not escalated"):
        claim.resolve_review(VerificationVerdict.VERIFIED, "no basis")


def test_unsupported_assertion_is_kept_and_drained() -> None:
    claim = Claim(id="clm_7", text="Eine Behauptung", type=ClaimType.LEGAL)  # type: ignore[arg-type]

    claim.mark_unsupported("no evidence above threshold")

    assert claim.verdict is VerificationVerdict.UNSUPPORTED
    assert isinstance(claim.events[0], UnsupportedAssertionFlagged)
    drained = claim.drain_events()
    assert len(drained) == 1
    assert claim.events == []
