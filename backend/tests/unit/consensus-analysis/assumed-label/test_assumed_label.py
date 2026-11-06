"""Contract freeze: assumed label (issue #305, implements #314)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from tests.unit.consensus_analysis_contract_helpers import (
    enum_values,
    field_names,
    parameter_names,
)

from consensus_analysis.application.dto import EstimatedFigureResult
from consensus_analysis.domain.services import EstimateValidator
from consensus_analysis.domain.values import (
    BasisKind,
    EstimateBasis,
    EstimatedFigure,
    UncertaintyLabel,
)


def test_the_label_vocabulary_is_closed() -> None:
    assert enum_values(UncertaintyLabel) == {"evidenced", "modelled", "assumed"}


def test_a_figure_persists_with_its_label() -> None:
    assert field_names(EstimatedFigure) == ["field", "value", "basis", "label", "limitation"]
    assert field_names(EstimatedFigureResult) == [
        "field",
        "value",
        "basis",
        "label",
        "limitation",
    ]


def test_labelling_a_basis_is_frozen() -> None:
    assert parameter_names(EstimateValidator.label_for) == ["self", "basis"]
    with pytest.raises(NotImplementedError, match="#314"):
        EstimateValidator().label_for(EstimateBasis(kind=BasisKind.ASSUMED))


def test_an_assumed_figure_cannot_claim_to_be_computed() -> None:
    figure = EstimatedFigure(
        field="waiting_times_p50_days",
        value=Decimal("22"),
        basis=EstimateBasis(kind=BasisKind.ASSUMED),
        label=UncertaintyLabel.ASSUMED,
    )
    assert parameter_names(EstimatedFigure.is_computable) == ["self"]
    with pytest.raises(NotImplementedError, match="#314"):
        figure.is_computable()
