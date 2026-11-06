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
    validator = EstimateValidator()
    assert validator.label_for(EstimateBasis(kind=BasisKind.MEASURED)) is (
        UncertaintyLabel.EVIDENCED
    )
    assert validator.label_for(EstimateBasis(kind=BasisKind.DERIVED)) is (UncertaintyLabel.MODELLED)
    assert validator.label_for(EstimateBasis(kind=BasisKind.ASSUMED)) is UncertaintyLabel.ASSUMED
    assert validator.label_for(EstimateBasis(kind=BasisKind.NOT_ESTIMATED)) is (
        UncertaintyLabel.ASSUMED
    )


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


# ── issue #314: the label is enforced, persisted, and carried on the wire ──────────────────────


def test_a_label_that_misstates_the_basis_is_refused() -> None:
    from consensus_analysis.domain.errors import MislabeledEstimate

    assumed_but_labelled_evidenced = EstimatedFigure(
        field="waiting_times_p50_days",
        value=Decimal("22"),
        basis=EstimateBasis(kind=BasisKind.ASSUMED),
        label=UncertaintyLabel.EVIDENCED,
    )
    with pytest.raises(MislabeledEstimate) as raised:
        EstimateValidator().validate(assumed_but_labelled_evidenced)
    assert raised.value.code == "MISLABELED_ESTIMATE"
    assert raised.value.expected == "assumed"

    modelled_but_labelled_assumed = EstimatedFigure(
        field="cost_eur",
        value=Decimal("1000000"),
        basis=EstimateBasis(kind=BasisKind.MODELLED),
        label=UncertaintyLabel.ASSUMED,
    )
    with pytest.raises(MislabeledEstimate):
        EstimateValidator().validate(modelled_but_labelled_assumed)


def test_an_honestly_labelled_figure_passes() -> None:
    EstimateValidator().validate(
        EstimatedFigure(
            field="waiting_times_p50_days",
            value=Decimal("22"),
            basis=EstimateBasis(kind=BasisKind.ASSUMED),
            label=UncertaintyLabel.ASSUMED,
        )
    )


def test_the_assessment_keeps_the_label_of_every_figure() -> None:
    from consensus_analysis.domain.entities import ImpactAssessment
    from consensus_analysis.domain.values import AssessmentId, PackageId, ScenarioId

    assumed = EstimatedFigure(
        field="waiting_times_p50_days",
        value=Decimal("22"),
        basis=EstimateBasis(kind=BasisKind.ASSUMED),
        label=UncertaintyLabel.ASSUMED,
    )
    assessment = ImpactAssessment.assess(
        scenario_id=ScenarioId("scn_1"),
        package_id=PackageId("pkg_1"),
        assessment_id=AssessmentId("imp_1"),
        figures=(assumed,),
    )
    assert assessment.figures[0].label is UncertaintyLabel.ASSUMED
    assert assessment.basis.kind is BasisKind.ASSUMED


def test_the_api_cannot_render_a_figure_without_its_label() -> None:
    """The wire schema has no default: an omitted label is a 422, not a silent 'computed'."""
    from pydantic import ValidationError

    from consensus_analysis.interfaces.http.schemas import EstimatedFigureBody

    with pytest.raises(ValidationError):
        EstimatedFigureBody.model_validate(
            {"field": "cost_eur", "value": "42", "basis": {"kind": "assumed"}}
        )

    labelled = EstimatedFigureBody.model_validate(
        {
            "field": "cost_eur",
            "value": "42",
            "basis": {"kind": "assumed", "inputs": []},
            "label": "assumed",
        }
    )
    assert labelled.label is UncertaintyLabel.ASSUMED


def test_the_api_response_shape_always_carries_basis_and_label() -> None:
    from consensus_analysis.interfaces.http.schemas import AssessImpactResponse

    figure_fields = AssessImpactResponse.model_json_schema()["$defs"]["EstimatedFigureBody"][
        "required"
    ]
    assert {"basis", "label"} <= set(figure_fields)
