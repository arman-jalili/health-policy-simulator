"""Contract freeze: unbacked estimate (issue #305, implements #313)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import ClassVar

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.application.commands import AssessImpactRequest
from consensus_analysis.application.dto import EstimateRequest
from consensus_analysis.application.estimators import (
    AssumedEstimator,
    DerivedEstimator,
    EstimateStrategy,
    MeasuredEstimator,
    ModelledEstimator,
)
from consensus_analysis.application.ports import LlmImpactEstimator, ReferenceFigures
from consensus_analysis.application.services import AssessImpact
from consensus_analysis.domain.compromise_package import CompromisePackage
from consensus_analysis.domain.entities import ImpactAssessment
from consensus_analysis.domain.errors import UnbackedEstimate
from consensus_analysis.domain.events import (
    DomainEvent,
    ImpactAssessed,
    UnbackedEstimateBlocked,
)
from consensus_analysis.domain.services import (
    EstimateValidator,
    FeasibilityGuard,
    IllustrativeValueGuard,
)
from consensus_analysis.domain.values import (
    AssessmentId,
    BaselineRef,
    BasisKind,
    DerivationInput,
    DerivationInputKind,
    EstimateBasis,
    EstimatedFigure,
    Horizon,
    LogPosition,
    PackageId,
    RunId,
    ScenarioAssumption,
    ScenarioId,
    UncertaintyLabel,
)
from consensus_analysis.infrastructure.acl import IllustrativeExampleCatalog


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
    with pytest.raises(UnbackedEstimate) as raised:
        EstimateValidator().validate(figure)
    assert raised.value.code == "UNBACKED_ESTIMATE"
    assert raised.value.field == "cost_eur"
    assert raised.value.claimed_basis == "derived"
    assert raised.value.details[0].field == "cost_eur"


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


def test_a_computed_basis_demands_inputs_and_an_unbacked_one_is_visible() -> None:
    unbacked = EstimateBasis(kind=BasisKind.DERIVED)
    backed = EstimateBasis(
        kind=BasisKind.DERIVED,
        inputs=(DerivationInput(kind=DerivationInputKind.TALLY, reference_id="tally_1"),),
    )
    assumed = EstimateBasis(kind=BasisKind.ASSUMED)
    assert unbacked.requires_inputs() is True
    assert unbacked.is_backed() is False
    assert backed.is_backed() is True
    assert assumed.requires_inputs() is False
    assert assumed.is_backed() is True


def test_an_assessment_reports_the_weakest_basis_of_its_figures() -> None:
    measured = EstimatedFigure(
        field="cost_eur",
        value=Decimal("1"),
        basis=EstimateBasis(
            kind=BasisKind.MEASURED,
            inputs=(DerivationInput(kind=DerivationInputKind.REFERENCE_FIGURE, reference_id="f1"),),
        ),
        label=UncertaintyLabel.EVIDENCED,
    )
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
        figures=(measured, assumed),
    )
    assert assessment.basis.kind is BasisKind.ASSUMED
    assert {(item.kind, item.reference_id) for item in assessment.basis.inputs} == {
        (DerivationInputKind.REFERENCE_FIGURE, "f1")
    }
    assert [figure.field for figure in assessment.figures] == [
        "cost_eur",
        "waiting_times_p50_days",
    ]


def test_an_assessment_without_figures_is_not_estimated() -> None:
    assessment = ImpactAssessment.assess(
        scenario_id=ScenarioId("scn_1"),
        package_id=PackageId("pkg_1"),
        assessment_id=AssessmentId("imp_1"),
        figures=(),
    )
    assert assessment.basis.kind is BasisKind.NOT_ESTIMATED


def test_the_request_makes_inputs_explicit() -> None:
    assert field_names(EstimateRequest) == ["scenario_id", "field", "inputs", "assumed_value"]


# ── issue #313: a computed basis without inputs is refused, and the refusal is published ──────


class _Publisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, events, *, trace_id=None):  # type: ignore[no-untyped-def]
        self.events.extend(events)


class _Packages:
    async def get(self, package_id):  # type: ignore[no-untyped-def]
        return CompromisePackage(id=package_id, run_id=RunId("run_1"), log_position=LogPosition(0))

    async def save(self, package) -> None:  # type: ignore[no-untyped-def]
        return None

    async def for_run(self, run_id):  # type: ignore[no-untyped-def]
        return []


class _Scenarios:
    async def get(self, scenario_id):  # type: ignore[no-untyped-def]
        return None

    async def save(self, scenario) -> None:  # type: ignore[no-untyped-def]
        return None

    async def for_package(self, package_id):  # type: ignore[no-untyped-def]
        return []


class _Ids:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_1"


class _UnitOfWork:
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[object]:
        yield None


class _UnbackedStrategy:
    """A strategy that claims a computed basis without enumerating anything."""

    basis: ClassVar[BasisKind] = BasisKind.DERIVED

    async def estimate(self, request: EstimateRequest) -> EstimatedFigure:
        return EstimatedFigure(
            field=request.field,
            value=Decimal("42"),
            basis=EstimateBasis(kind=BasisKind.DERIVED),
            label=UncertaintyLabel.MODELLED,
        )


def _assess_impact(publisher: _Publisher) -> AssessImpact:
    from consensus_analysis.application.services import AssessImpact

    return AssessImpact(
        packages=_Packages(),
        scenarios=_Scenarios(),
        estimation={BasisKind.DERIVED: _UnbackedStrategy()},
        validator=EstimateValidator(),
        illustrative=IllustrativeValueGuard(),
        catalogue=IllustrativeExampleCatalog(examples=()),
        feasibility=FeasibilityGuard(),
        events=publisher,
        ids=_Ids(),
        uow=_UnitOfWork(),
    )


async def test_an_unbacked_estimate_is_refused_and_blocked_in_the_audit_trail() -> None:
    publisher = _Publisher()
    request = AssessImpactRequest(
        package_id=PackageId("pkg_1"),
        baseline=BaselineRef(label="status quo 2026"),
        horizon=Horizon(years=5),
        assumptions=(
            ScenarioAssumption(
                statement="cost_eur",
                basis=EstimateBasis(kind=BasisKind.DERIVED),
            ),
        ),
    )

    with pytest.raises(UnbackedEstimate):
        await _assess_impact(publisher).execute(request)

    blocked = [event for event in publisher.events if isinstance(event, UnbackedEstimateBlocked)]
    assert len(blocked) == 1
    assert blocked[0].field == "cost_eur"
    assert blocked[0].claimed_basis is BasisKind.DERIVED
    assert blocked[0].scenario_id == ScenarioId("scn_1")


async def test_an_honest_assumed_estimate_passes_the_same_gate() -> None:
    from consensus_analysis.application.services import AssessImpact

    publisher = _Publisher()
    service = AssessImpact(
        packages=_Packages(),
        scenarios=_Scenarios(),
        estimation={BasisKind.ASSUMED: AssumedEstimator()},
        validator=EstimateValidator(),
        illustrative=IllustrativeValueGuard(),
        catalogue=IllustrativeExampleCatalog(examples=()),
        feasibility=FeasibilityGuard(),
        events=publisher,
        ids=_Ids(),
        uow=_UnitOfWork(),
    )
    service._estimation = {BasisKind.ASSUMED: AssumedEstimator()}

    class _Seeded(AssumedEstimator):
        async def estimate(self, request):  # type: ignore[no-untyped-def]
            from consensus_analysis.application.dto import EstimateRequest

            return await super().estimate(
                EstimateRequest(
                    scenario_id=request.scenario_id,
                    field=request.field,
                    assumed_value=Decimal("22"),
                )
            )

    service._estimation = {BasisKind.ASSUMED: _Seeded()}
    result = await service.execute(
        AssessImpactRequest(
            package_id=PackageId("pkg_1"),
            baseline=BaselineRef(label="status quo 2026"),
            horizon=Horizon(years=5),
            assumptions=(
                ScenarioAssumption(
                    statement="waiting_times_p50_days",
                    basis=EstimateBasis(kind=BasisKind.ASSUMED),
                ),
            ),
        )
    )

    assert result.figures[0].label is UncertaintyLabel.ASSUMED
    assert any(isinstance(event, ImpactAssessed) for event in publisher.events)
