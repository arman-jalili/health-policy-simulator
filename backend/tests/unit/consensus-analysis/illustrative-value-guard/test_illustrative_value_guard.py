"""Contract freeze: illustrative-value guard (issue #305, implements #315)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.application.commands import AssessImpactRequest
from consensus_analysis.domain.compromise_package import CompromisePackage
from consensus_analysis.domain.errors import IllustrativeValueRefused
from consensus_analysis.domain.scenario import Scenario
from consensus_analysis.domain.services import (
    EstimateValidator,
    FeasibilityGuard,
    IllustrativeValueGuard,
)
from consensus_analysis.domain.values import (
    BasisKind,
    DocumentedExample,
    EstimateBasis,
    EstimatedFigure,
    LogPosition,
    PackageId,
    RunId,
    ScenarioId,
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
    with pytest.raises(IllustrativeValueRefused) as raised:
        IllustrativeValueGuard().refuse(figure, examples)
    assert raised.value.code == "ILLUSTRATIVE_VALUE_REFUSED"
    assert raised.value.field == "waiting_times_p50_days"
    assert raised.value.source == "docs/runbook.md"


def test_the_catalogue_is_the_published_list_of_examples() -> None:
    examples = (DocumentedExample(value=Decimal("22"), source="docs/runbook.md"),)
    catalogue = IllustrativeExampleCatalog(examples=examples)
    assert catalogue.examples() == examples


# ── issue #315: the demo number cannot become an outcome ───────────────────────────────────────


def _figure(value: str, field: str = "waiting_times_p50_days") -> EstimatedFigure:
    return EstimatedFigure(
        field=field,
        value=Decimal(value),
        basis=EstimateBasis(kind=BasisKind.ASSUMED),
        label=UncertaintyLabel.ASSUMED,
    )


def test_a_documented_example_is_refused_however_it_is_written() -> None:
    catalogue = (DocumentedExample(value=Decimal("22.00"), source="docs/runbook.md"),)
    for rendered in ("22", "22.0", "22.000"):
        with pytest.raises(IllustrativeValueRefused):
            IllustrativeValueGuard().refuse(_figure(rendered), catalogue)


def test_a_figure_that_is_not_a_documented_example_passes() -> None:
    catalogue = (DocumentedExample(value=Decimal("22"), source="docs/runbook.md"),)
    IllustrativeValueGuard().refuse(_figure("23.4"), catalogue)


def test_an_empty_catalogue_refuses_nothing() -> None:
    IllustrativeValueGuard().refuse(_figure("22"), ())


def test_the_refusal_names_the_document_that_contains_the_example() -> None:
    catalogue = (DocumentedExample(value=Decimal("22"), source="docs/dr-plan.md"),)
    with pytest.raises(IllustrativeValueRefused) as raised:
        IllustrativeValueGuard().refuse(_figure("22"), catalogue)
    assert "docs/dr-plan.md" in raised.value.message


async def test_the_persistence_path_refuses_an_illustrative_value_before_writing() -> None:
    """AC 7 end to end: the assessment is never saved when a figure is a demo number."""
    from consensus_analysis.application.estimators import AssumedEstimator
    from consensus_analysis.application.services import AssessImpact
    from consensus_analysis.domain.values import (
        BaselineRef,
        Horizon,
        LogPosition,
        PackageId,
        RunId,
        ScenarioAssumption,
        ScenarioId,
    )

    class _SeededAssumed(AssumedEstimator):
        async def estimate(self, request: object) -> EstimatedFigure:
            return EstimatedFigure(
                field="waiting_times_p50_days",
                value=Decimal("22"),
                basis=EstimateBasis(kind=BasisKind.ASSUMED),
                label=UncertaintyLabel.ASSUMED,
            )

    scenarios = _Scenarios()
    service = AssessImpact(
        packages=_Packages(),
        scenarios=scenarios,
        estimation={BasisKind.ASSUMED: _SeededAssumed()},
        validator=EstimateValidator(),
        illustrative=IllustrativeValueGuard(),
        catalogue=IllustrativeExampleCatalog(
            examples=(DocumentedExample(value=Decimal("22"), source="docs/runbook.md"),)
        ),
        feasibility=FeasibilityGuard(),
        events=_Events(),
        ids=_Ids(),
        uow=_UnitOfWork(),
    )

    with pytest.raises(IllustrativeValueRefused):
        await service.execute(
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

    assert scenarios.saved == []
    assert LogPosition(0) is not None
    assert RunId("run_1") is not None
    assert ScenarioId("scn_1") is not None


class _Events:
    async def publish(self, events: object, *, trace_id: str | None = None) -> None:
        return None


class _Ids:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_1"


class _UnitOfWork:
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[object]:
        yield None


class _Packages:
    async def get(self, package_id: PackageId) -> CompromisePackage:
        return CompromisePackage(id=package_id, run_id=RunId("run_1"), log_position=LogPosition(0))

    async def save(self, package: CompromisePackage) -> None:
        return None

    async def for_run(self, run_id: RunId) -> list[CompromisePackage]:
        return []


class _Scenarios:
    def __init__(self) -> None:
        self.saved: list[Scenario] = []

    async def get(self, scenario_id: ScenarioId) -> Scenario | None:
        return None

    async def save(self, scenario: Scenario) -> None:
        self.saved.append(scenario)

    async def for_package(self, package_id: PackageId) -> list[Scenario]:
        return []
