"""Contract freeze: German numeric parsing adapter (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import method_names, parameter_names

from claim_validation.infrastructure.number_parser import GermanNumberParser


def test_parser_is_an_infrastructure_adapter() -> None:
    assert GermanNumberParser.__module__ == "claim_validation.infrastructure.number_parser"
    assert "parse" in method_names(GermanNumberParser)
    assert parameter_names(GermanNumberParser.parse) == ["self", "text"]
