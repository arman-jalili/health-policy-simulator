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
    DerivationInput,
    DerivationInputKind,
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
    assert figure.is_computable() is False


def test_a_backed_computed_figure_may_be_rendered() -> None:
    figure = EstimatedFigure(
        field="cost_eur",
        value=Decimal("1000000"),
        basis=EstimateBasis(
            kind=BasisKind.DERIVED,
            inputs=(DerivationInput(kind=DerivationInputKind.TALLY, reference_id="tally_1"),),
        ),
        label=UncertaintyLabel.MODELLED,
    )
    assert figure.is_computable() is True


def test_an_assumed_label_beats_a_computed_basis() -> None:
    """Label and basis must agree; an assumed label can never travel as a calculation."""
    figure = EstimatedFigure(
        field="cost_eur",
        value=Decimal("1000000"),
        basis=EstimateBasis(
            kind=BasisKind.DERIVED,
            inputs=(DerivationInput(kind=DerivationInputKind.TALLY, reference_id="tally_1"),),
        ),
        label=UncertaintyLabel.ASSUMED,
    )
    assert figure.is_computable() is False
