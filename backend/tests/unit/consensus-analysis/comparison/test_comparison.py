"""Contract freeze: comparison (issue #305, implements #319)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.application.commands import CompareScenariosRequest
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


def test_an_entry_carries_all_three_dimensions() -> None:
    entry = ComparisonEntryResult(
        package_id=PackageId("pkg_1"),
        scenario_id=ScenarioId("scn_1"),
        cost=Decimal("1000000"),
        acceptance=0.78,
        feasibility=_feasibility(),
        rank=1,
    )
    assert entry.cost == Decimal("1000000")
    assert entry.acceptance == pytest.approx(0.78)
    assert entry.feasibility.is_fully_rated() is True


# ── issue #319: alternatives are ranked with all three dimensions present ─────────────────────


def _entry(
    scenario: str,
    *,
    cost: str,
    acceptance: float,
    political: FeasibilityLevel = FeasibilityLevel.MEDIUM,
) -> ComparisonEntryResult:
    return ComparisonEntryResult(
        package_id=PackageId("pkg_1"),
        scenario_id=ScenarioId(scenario),
        cost=Decimal(cost),
        acceptance=acceptance,
        feasibility=FeasibilityRating(
            political=political,
            legal=FeasibilityLevel.HIGH,
            administrative=FeasibilityLevel.MEDIUM,
            basis=EstimateBasis(kind=BasisKind.MODELLED),
        ),
        rank=1,
    )


def test_ranking_is_deterministic_and_complete() -> None:
    from consensus_analysis.infrastructure.comparison import LexicographicRanker

    entries = (
        _entry("scn_low", cost="100", acceptance=0.4),
        _entry("scn_high", cost="900", acceptance=0.9),
        _entry("scn_mid", cost="500", acceptance=0.6),
    )

    ranked = LexicographicRanker().rank(entries)

    assert [(entry.scenario_id, entry.rank) for entry in ranked] == [
        ("scn_high", 1),
        ("scn_mid", 2),
        ("scn_low", 3),
    ]
    assert all(entry.cost is not None for entry in ranked)
    assert all(entry.feasibility.is_fully_rated() for entry in ranked)


def test_acceptance_dominates_then_feasibility_then_cost() -> None:
    from consensus_analysis.infrastructure.comparison import LexicographicRanker

    entries = (
        _entry("scn_cheap_infeasible", cost="1", acceptance=0.5, political=FeasibilityLevel.LOW),
        _entry("scn_dear_feasible", cost="9999", acceptance=0.5, political=FeasibilityLevel.HIGH),
    )

    ranked = LexicographicRanker().rank(entries)

    assert [entry.scenario_id for entry in ranked] == [
        "scn_dear_feasible",
        "scn_cheap_infeasible",
    ]


def test_ranking_preserves_every_dimension_it_used() -> None:
    from consensus_analysis.infrastructure.comparison import LexicographicRanker

    ranker = LexicographicRanker()
    ranked = ranker.rank((_entry("scn_1", cost="100", acceptance=0.7),))

    assert ranker.dimensions() == (
        ComparisonDimension.ACCEPTANCE,
        ComparisonDimension.FEASIBILITY,
        ComparisonDimension.COST,
    )
    assert ranked[0].cost == Decimal("100")
    assert ranked[0].acceptance == pytest.approx(0.7)
    assert ranked[0].feasibility.legal is FeasibilityLevel.HIGH


async def test_an_alternative_without_feasibility_is_refused_not_partially_ranked() -> None:
    from consensus_analysis.application.services import CompareScenarios
    from consensus_analysis.domain.compromise_package import CompromisePackage
    from consensus_analysis.domain.errors import IncompleteComparison
    from consensus_analysis.domain.scenario import Scenario
    from consensus_analysis.domain.values import (
        BaselineRef,
        Horizon,
        LogPosition,
        RunId,
    )
    from consensus_analysis.infrastructure.comparison import LexicographicRanker

    class _Packages:
        async def get(self, package_id: PackageId) -> CompromisePackage:
            return CompromisePackage(
                id=package_id, run_id=RunId("run_1"), log_position=LogPosition(0)
            )

        async def save(self, package: CompromisePackage) -> None:
            return None

        async def for_run(self, run_id: RunId) -> list[CompromisePackage]:
            return []

    class _Scenarios:
        async def get(self, scenario_id: ScenarioId) -> Scenario | None:
            return None

        async def save(self, scenario: Scenario) -> None:
            return None

        async def for_package(self, package_id: PackageId) -> list[Scenario]:
            return [
                Scenario(
                    id=ScenarioId("scn_1"),
                    package_id=package_id,
                    baseline=BaselineRef(label="status quo"),
                    horizon=Horizon(years=5),
                    log_position=LogPosition(0),
                )
            ]

    class _Consensus:
        async def get(self, consensus_id: object) -> None:
            return None

        async def save(self, record: object) -> None:
            return None

        async def for_run(self, run_id: RunId) -> list[object]:
            return []

        async def replace_for_run(self, run_id: RunId, records: object) -> None:
            return None

    service = CompareScenarios(
        packages=_Packages(),
        scenarios=_Scenarios(),
        consensus=_Consensus(),  # type: ignore[arg-type]
        ranker=LexicographicRanker(),
    )

    with pytest.raises(IncompleteComparison) as raised:
        await service.execute(CompareScenariosRequest(package_id=PackageId("pkg_1")))
    assert "cost" in raised.value.missing or "feasibility" in raised.value.missing
