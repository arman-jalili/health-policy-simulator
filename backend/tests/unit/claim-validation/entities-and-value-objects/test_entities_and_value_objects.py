"""Contract freeze: entities and value objects (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import enum_values, field_names

from claim_validation.domain.entities import ClaimVerification, ContradictionFinding, ExpertReview
from claim_validation.domain.values import (
    CausalSupport,
    ClaimType,
    MeasureReference,
    ReferenceFigure,
    ToleranceBand,
    VerificationEvidence,
    VerificationPath,
    VerificationVerdict,
)


def test_claim_type_and_verdict_vocabulary_is_frozen() -> None:
    assert enum_values(ClaimType) == {"quantitative", "legal", "causal", "qualitative"}
    assert enum_values(VerificationVerdict) == {
        "pending",
        "verified",
        "contradicted",
        "unsupported",
        "ambiguous",
    }
    assert enum_values(VerificationPath) == {
        "quantitative",
        "legal",
        "causal",
        "qualitative",
    }
    assert enum_values(CausalSupport) == {"supported", "contested", "unaddressed"}


def test_value_objects_expose_required_fields() -> None:
    assert field_names(MeasureReference) == ["measure", "unit", "period", "geography"]
    assert field_names(ToleranceBand) == ["relative"]
    assert field_names(ReferenceFigure) == ["id", "measure", "value", "tier", "as_of", "source_id"]
    assert field_names(VerificationEvidence) == [
        "sources",
        "reference_figure",
        "asserted_value",
        "asserted_measure",
        "method",
        "support",
        "study_ids",
    ]


def test_entities_expose_audit_fields() -> None:
    assert field_names(ClaimVerification) == [
        "verdict",
        "path",
        "sources",
        "method",
        "reference_id",
        "asserted_value",
        "reference_value",
        "delta",
    ]
    assert field_names(ContradictionFinding) == [
        "id",
        "claim_id_a",
        "claim_id_b",
        "measure",
        "delta",
    ]
    assert field_names(ExpertReview) == ["id", "question", "verdict", "basis"]


# --- behaviour: VO invariants and immutability (issue #166) ----------------------------------

from dataclasses import FrozenInstanceError  # noqa: E402
from datetime import date  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

from evidence_corpus.domain.values import AuthorityTier  # noqa: E402


def _measure() -> MeasureReference:
    return MeasureReference("Kassenstellen", "count", "2026", "AT")


def test_value_objects_are_immutable() -> None:
    measure = _measure()

    with pytest.raises(FrozenInstanceError):
        measure.unit = "percent"  # type: ignore[misc]


def test_measure_identity_requires_every_dimension() -> None:
    with pytest.raises(ValueError, match="measure must not be empty"):
        MeasureReference("", "count", "2026", "AT")


def test_tolerance_band_rejects_impossible_relative_values() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        ToleranceBand(Decimal("-0.1"))
    with pytest.raises(ValueError, match="between 0 and 1"):
        ToleranceBand(Decimal("1.1"))


def test_reference_figure_rejects_negative_values_and_missing_sources() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        ReferenceFigure(
            id="fig_1",  # type: ignore[arg-type]
            measure=_measure(),
            value=Decimal("-1"),
            tier=AuthorityTier.OFFICIAL_STATISTICS,
            as_of=date(2026, 1, 1),
            source_id="src_1",
        )
    with pytest.raises(ValueError, match="source id"):
        ReferenceFigure(
            id="fig_1",  # type: ignore[arg-type]
            measure=_measure(),
            value=Decimal("1"),
            tier=AuthorityTier.OFFICIAL_STATISTICS,
            as_of=date(2026, 1, 1),
            source_id=" ",
        )


def test_verification_is_an_immutable_audit_record() -> None:
    verification = ClaimVerification(
        verdict=VerificationVerdict.VERIFIED,
        path=VerificationPath.LEGAL,
        sources=("passage_1",),
        method="provision_match",
    )

    assert verification.sources == ("passage_1",)
    with pytest.raises(FrozenInstanceError):
        verification.method = "other"  # type: ignore[misc]
