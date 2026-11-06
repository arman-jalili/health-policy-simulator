"""Contract freeze: comparison (issue #305, implements #319)."""

from __future__ import annotations

from decimal import Decimal

from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.application.dto import ComparisonEntryResult
from consensus_analysis.application.ports import ComparisonRanker
from consensus_analysis.application.services import CompareScenarios
from consensus_analysis.domain.values import (
    BasisKind,
    ComparisonDimension,
    EstimateBasis,
    FeasibilityLevel,
    FeasibilityRating,
    PackageId,
    ScenarioId,
)


def _feasibility() -> FeasibilityRating:
    return FeasibilityRating(
        political=FeasibilityLevel.MEDIUM,
        legal=FeasibilityLevel.HIGH,
        administrative=FeasibilityLevel.MEDIUM,
        basis=EstimateBasis(kind=BasisKind.MODELLED),
    )


def test_all_three_dimensions_are_mandatory_on_an_entry() -> None:
    assert field_names(ComparisonEntryResult) == [
        "package_id",
        "scenario_id",
        "cost",
        "acceptance",
        "feasibility",
        "rank",
    ]
    assert {dimension.value for dimension in ComparisonDimension} == {
        "cost",
        "acceptance",
        "feasibility",
    }


def test_ranking_is_a_separate_strategy() -> None:
    assert parameter_names(ComparisonRanker.rank) == ["self", "entries"]


def test_compare_scenarios_requires_the_consensus_projection() -> None:
    service = CompareScenarios(
        packages=None,  # type: ignore[arg-type]
        scenarios=None,  # type: ignore[arg-type]
        consensus=None,  # type: ignore[arg-type]
        ranker=None,  # type: ignore[arg-type]
    )
    assert len(service.collaborators()) == 4


def test_compare_is_not_implemented_yet() -> None:
    entry = ComparisonEntryResult(
        package_id=PackageId("pkg_1"),
        scenario_id=ScenarioId("scn_1"),
        cost=Decimal("1000000"),
        acceptance=0.78,
        feasibility=_feasibility(),
        rank=1,
    )
    assert entry.cost == Decimal("1000000")
