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


# --- behaviour: press-tier values are refused (issue #173) ----------------------------------

from datetime import date  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

from claim_validation.domain.values import MeasureReference  # noqa: E402
from evidence_corpus.domain.values import AuthorityTier  # noqa: E402


def _measure() -> MeasureReference:
    return MeasureReference("Kassenstellen", "count", "2026", "AT")


def test_press_tier_reference_is_refused() -> None:
    with pytest.raises(ReferenceFigureNotAuthoritative, match="press reports"):
        ReferenceFigure(
            id="fig_press",  # type: ignore[arg-type]
            measure=_measure(),
            value=Decimal("3.2"),
            tier=AuthorityTier.PRESS_REPORT,
            as_of=date(2026, 1, 1),
            source_id="newspaper_1",
        )


def test_authoritative_tier_is_accepted() -> None:
    figure = ReferenceFigure(
        id="fig_official",  # type: ignore[arg-type]
        measure=_measure(),
        value=Decimal("3.2"),
        tier=AuthorityTier.OFFICIAL_STATISTICS,
        as_of=date(2026, 1, 1),
        source_id="statistik_austria_1",
    )

    assert figure.tier is AuthorityTier.OFFICIAL_STATISTICS
    assert figure.source_id == "statistik_austria_1"
