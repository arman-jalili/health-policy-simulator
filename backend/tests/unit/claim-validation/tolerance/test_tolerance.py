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


# --- behaviour: 2% band arithmetic (issue #171) ---------------------------------------------

from decimal import Decimal as _Decimal  # noqa: E402


def test_rounding_is_not_a_contradiction() -> None:
    band = ToleranceBand()
    within, delta = FigureComparison().compare(_Decimal("3.25"), _Decimal("3.2"), band)

    assert within is True
    assert delta == _Decimal("0.05")


def test_material_difference_exceeds_the_band() -> None:
    within, delta = FigureComparison().compare(_Decimal("4.1"), _Decimal("3.2"), ToleranceBand())

    assert within is False
    assert delta == _Decimal("0.9")


def test_band_boundary_is_inclusive() -> None:
    band = ToleranceBand(relative=_Decimal("0.10"))

    assert band.contains(_Decimal("2.2"), _Decimal("2.0")) is True
    assert band.contains(_Decimal("2.2001"), _Decimal("2.0")) is False


def test_zero_reference_requires_exact_equality() -> None:
    assert ToleranceBand().contains(_Decimal("0"), _Decimal("0")) is True
    assert ToleranceBand().contains(_Decimal("0.01"), _Decimal("0")) is False
