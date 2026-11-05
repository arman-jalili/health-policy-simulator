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
