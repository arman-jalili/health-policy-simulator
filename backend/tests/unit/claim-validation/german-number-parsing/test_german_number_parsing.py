"""Contract freeze: German numeric parsing adapter (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import method_names, parameter_names

from claim_validation.infrastructure.number_parser import GermanNumberParser


def test_parser_is_an_infrastructure_adapter() -> None:
    assert GermanNumberParser.__module__ == "claim_validation.infrastructure.number_parser"
    assert "parse" in method_names(GermanNumberParser)
    assert parameter_names(GermanNumberParser.parse) == ["self", "text"]


# --- behaviour: German formats (issue #176) -------------------------------------------------

from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402


@pytest.mark.parametrize(
    ("text", "value", "unit"),
    [
        ("1.204 Kassenstellen", Decimal("1204"), "count"),
        ("3,2 Mrd. €", Decimal("3200000000"), "EUR"),
        ("22 %", Decimal("22"), "percent"),
        ("1.204,50 Euro", Decimal("1204.50"), "EUR"),
        ("3,25 Mio. Kassenstellen", Decimal("3250000"), "count"),
        ("22 Prozent", Decimal("22"), "percent"),
    ],
)
def test_german_numbers_parse_to_base_values(text: str, value: Decimal, unit: str) -> None:
    assert GermanNumberParser().parse(text) == (value, unit)


def test_text_without_a_number_returns_none() -> None:
    assert GermanNumberParser().parse("keine Zahl enthalten") is None


# --- behaviour: refuse ambiguous figures (issue #202) ---------------------------------------

from decimal import Decimal as _Decimal  # noqa: E402


def test_a_leading_year_makes_the_parse_ambiguous() -> None:
    assert GermanNumberParser().parse("Im Jahr 2026 gibt es 3.200.000 Kassenstellen") is None


def test_a_year_is_never_multiplied_by_a_later_scale() -> None:
    assert GermanNumberParser().parse("Bis 2027 sollen 1,2 Mrd. Euro fliessen") is None


def test_a_single_year_without_a_unit_is_refused() -> None:
    assert GermanNumberParser().parse("Im Jahr 2026") is None


def test_scale_comes_from_the_immediate_phrase_only() -> None:
    assert GermanNumberParser().parse("1,2 Mrd. Euro, spaeter Mio. Angaben") == (
        _Decimal("1200000000"),
        "EUR",
    )


def test_multiple_candidate_numbers_are_refused() -> None:
    assert GermanNumberParser().parse("3,2 Mrd. Euro und spaeter 4,5 Mio. Euro") is None
