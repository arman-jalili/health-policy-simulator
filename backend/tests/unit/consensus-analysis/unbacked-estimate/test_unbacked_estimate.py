"""Contract freeze: unbacked estimate (issue #305, implements #313)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.application.dto import EstimateRequest
from consensus_analysis.application.estimators import (
    AssumedEstimator,
    DerivedEstimator,
    EstimateStrategy,
    MeasuredEstimator,
    ModelledEstimator,
)
from consensus_analysis.application.ports import LlmImpactEstimator, ReferenceFigures
from consensus_analysis.domain.entities import ImpactAssessment
from consensus_analysis.domain.errors import UnbackedEstimate
from consensus_analysis.domain.events import UnbackedEstimateBlocked
from consensus_analysis.domain.services import EstimateValidator
from consensus_analysis.domain.values import (
    BasisKind,
    DerivationInput,
    DerivationInputKind,
    EstimateBasis,
    EstimatedFigure,
    PackageId,
    ScenarioId,
    UncertaintyLabel,
)


def test_the_refusal_is_a_stable_error_code() -> None:
    assert UnbackedEstimate.code == "UNBACKED_ESTIMATE"
    assert UnbackedEstimate.status_code == 422


def test_an_input_is_an_enumerated_reference() -> None:
    assert field_names(DerivationInput) == ["kind", "reference_id", "description"]
    assert DerivationInputKind.REFERENCE_FIGURE.value == "reference_figure"


def test_basis_carries_its_inputs() -> None:
    assert field_names(EstimateBasis) == ["kind", "inputs"]
    assert parameter_names(EstimateBasis.requires_inputs) == ["self"]
    assert parameter_names(EstimateBasis.is_backed) == ["self"]


def test_the_validator_refuses_an_unbacked_derived_figure() -> None:
    assert parameter_names(EstimateValidator.validate) == ["self", "figure"]
    figure = EstimatedFigure(
        field="cost_eur",
        value=Decimal("1000000"),
        basis=EstimateBasis(kind=BasisKind.DERIVED),
        label=UncertaintyLabel.MODELLED,
    )
    with pytest.raises(NotImplementedError, match="#313"):
        EstimateValidator().validate(figure)


def test_the_blocked_event_records_the_claim_it_refused() -> None:
    assert field_names(UnbackedEstimateBlocked) == ["scenario_id", "field", "claimed_basis"]
    assert UnbackedEstimateBlocked.name == "UnbackedEstimateBlocked"


def test_one_strategy_per_basis() -> None:
    assert MeasuredEstimator.basis is BasisKind.MEASURED
    assert DerivedEstimator.basis is BasisKind.DERIVED
    assert ModelledEstimator.basis is BasisKind.MODELLED
    assert AssumedEstimator.basis is BasisKind.ASSUMED
    assert isinstance(MeasuredEstimator(), EstimateStrategy)


def test_the_metered_model_client_is_a_port_not_a_sdk() -> None:
    assert parameter_names(LlmImpactEstimator.estimate) == [
        "self",
        "scenario_id",
        "field",
        "context",
    ]
    assert parameter_names(ModelledEstimator.collaborators) == ["self"]
    assert parameter_names(ReferenceFigures.resolve) == ["self", "reference_figure_id"]


def test_a_computed_basis_without_inputs_is_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError, match="#313"):
        EstimateBasis(kind=BasisKind.DERIVED).requires_inputs()
    with pytest.raises(NotImplementedError, match="#313"):
        ImpactAssessment.assess(
            scenario_id=ScenarioId("scn_1"),
            package_id=PackageId("pkg_1"),
            figures=(),
        )


def test_the_request_makes_inputs_explicit() -> None:
    assert field_names(EstimateRequest) == ["scenario_id", "field", "inputs", "assumed_value"]
