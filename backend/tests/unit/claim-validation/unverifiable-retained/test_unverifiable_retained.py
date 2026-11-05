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


# --- behaviour: qualitative claims remain first-class (issue #170) ---------------------------

from claim_validation.domain.claim import Claim  # noqa: E402
from claim_validation.domain.values import (  # noqa: E402
    ClaimId,
    ClaimType,
    VerificationEvidence,
    VerificationPath,
    VerificationVerdict,
)


def test_qualitative_claim_keeps_its_identity_and_event() -> None:
    claim = Claim(
        id=ClaimId("clm_qual"), text="Die Stimmung ist angespannt", type=ClaimType.QUALITATIVE
    )

    claim.verify(VerificationPath.QUALITATIVE, VerificationEvidence())

    assert claim.id == "clm_qual"
    assert claim.verdict is VerificationVerdict.AMBIGUOUS
    event = claim.events[0]
    assert isinstance(event, ClaimMarkedUnverifiable)
    assert event.claim_id == "clm_qual"
    assert event.claim_type is ClaimType.QUALITATIVE


def test_unverifiable_claim_is_not_converted_to_unsupported() -> None:
    claim = Claim(
        id=ClaimId("clm_qual2"), text="Die Stimmung ist angespannt", type=ClaimType.QUALITATIVE
    )

    claim.verify(VerificationPath.QUALITATIVE, VerificationEvidence())

    assert claim.verdict is not VerificationVerdict.UNSUPPORTED
    assert claim.verification is not None
    assert claim.verification.method == "no_applicable_path"
