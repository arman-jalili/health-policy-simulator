"""Contract freeze: illustrative-value guard (issue #305, implements #315)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.errors import IllustrativeValueRefused
from consensus_analysis.domain.services import IllustrativeValueGuard
from consensus_analysis.domain.values import (
    BasisKind,
    DocumentedExample,
    EstimateBasis,
    EstimatedFigure,
    UncertaintyLabel,
)
from consensus_analysis.infrastructure.acl import IllustrativeExampleCatalog


def test_the_refusal_is_a_stable_error_code() -> None:
    assert IllustrativeValueRefused.code == "ILLUSTRATIVE_VALUE_REFUSED"
    assert IllustrativeValueRefused.status_code == 422


def test_a_documented_example_is_a_value_with_a_source() -> None:
    assert field_names(DocumentedExample) == ["value", "source", "description"]
    with pytest.raises(ValueError, match="source"):
        DocumentedExample(value=Decimal("22"), source=" ")


def test_the_guard_signature_is_frozen() -> None:
    assert parameter_names(IllustrativeValueGuard.refuse) == ["self", "figure", "examples"]
    figure = EstimatedFigure(
        field="waiting_times_p50_days",
        value=Decimal("22"),
        basis=EstimateBasis(kind=BasisKind.MODELLED),
        label=UncertaintyLabel.MODELLED,
    )
    examples = (DocumentedExample(value=Decimal("22"), source="docs/runbook.md"),)
    with pytest.raises(NotImplementedError, match="#315"):
        IllustrativeValueGuard().refuse(figure, examples)


def test_the_catalogue_is_the_published_list_of_examples() -> None:
    examples = (DocumentedExample(value=Decimal("22"), source="docs/runbook.md"),)
    catalogue = IllustrativeExampleCatalog(examples=examples)
    assert catalogue.examples() == examples
