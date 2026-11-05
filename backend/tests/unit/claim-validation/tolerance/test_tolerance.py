"""Contract freeze: tolerance is explicit arithmetic (issue #164)."""

from __future__ import annotations

from decimal import Decimal

from tests.unit.claim_validation_contract_helpers import field_names, parameter_names

from claim_validation.domain.services import FigureComparison
from claim_validation.domain.values import ToleranceBand


def test_band_is_relative_and_explicit() -> None:
    assert field_names(ToleranceBand) == ["relative"]
    assert ToleranceBand().relative == Decimal("0.02")


def test_comparison_takes_the_band_as_an_argument() -> None:
    assert parameter_names(FigureComparison.compare) == [
        "self",
        "asserted",
        "reference",
        "band",
    ]
