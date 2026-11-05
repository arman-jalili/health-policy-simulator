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
