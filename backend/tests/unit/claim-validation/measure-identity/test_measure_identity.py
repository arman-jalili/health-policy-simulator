"""Contract freeze: measure identity normalisation (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names, parameter_names

from claim_validation.domain.services import ResolveMeasureIdentity
from claim_validation.domain.values import MeasureReference


def test_measure_identity_has_four_dimensions() -> None:
    assert field_names(MeasureReference) == ["measure", "unit", "period", "geography"]


def test_resolution_takes_each_dimension_explicitly() -> None:
    assert parameter_names(ResolveMeasureIdentity.resolve) == [
        "self",
        "measure",
        "unit",
        "period",
        "geography",
    ]


# --- behaviour: normalisation without collapsing distinct measures (issue #177) --------------

from claim_validation.domain.services import ResolveMeasureIdentity as _Resolve  # noqa: E402


def test_whitespace_and_case_normalise_to_one_identity() -> None:
    service = _Resolve()

    first = service.resolve("  Wartezeit  ", "Tage", "2026", "Österreich")
    second = service.resolve("wartezeit", "tage", "2026", "AT")

    assert first == second
    assert first.measure == "wartezeit"
    assert first.geography == "AT"


def test_specific_measures_do_not_collapse() -> None:
    service = _Resolve()

    broad = service.resolve("Wartezeit", "Tage", "2026", "AT")
    specific = service.resolve("Wartezeit auf Facharzttermin", "Tage", "2026", "AT")

    assert broad != specific
    assert broad.measure != specific.measure


def test_unit_and_geography_aliases_are_canonical() -> None:
    service = _Resolve()

    assert service.resolve("Kosten", "Mrd. €", "2026", "österreich").unit == "Mrd. €"
    assert service.resolve("Anteil", "Prozent", "2026", "AT").unit == "percent"
    assert service.resolve("Kosten", "EUR", "2026", "Austria").geography == "AT"
