"""Contract freeze: reference figures carry provenance (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names

from claim_validation.domain.errors import ReferenceFigureNotAuthoritative
from claim_validation.domain.values import ReferenceFigure


def test_reference_figure_records_tier_date_and_source() -> None:
    assert field_names(ReferenceFigure) == [
        "id",
        "measure",
        "value",
        "tier",
        "as_of",
        "source_id",
    ]


def test_press_tier_refusal_is_a_validation_error() -> None:
    assert ReferenceFigureNotAuthoritative.code == "REFERENCE_FIGURE_NOT_AUTHORITATIVE"
    assert ReferenceFigureNotAuthoritative.status_code == 422
