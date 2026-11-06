"""Frozen composition factory of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Wiring Contract)

The factory intentionally is not called by ``shared/app.py`` until the runtime-integration issue. It
names every dependency the runtime must provide: the run log and veto rights of NegotiationSession
and StakeholderModel, verified figures of ClaimValidation, the metered model client, the
documentation-example catalogue and the rebuild strategy.
"""

from __future__ import annotations

from dataclasses import dataclass

from consensus_analysis.application.estimators import EstimateStrategy
from consensus_analysis.application.ports import (
    ComparisonRanker,
    EventPublisher,
    IllustrativeValueSource,
    LlmImpactEstimator,
    ProjectionRebuilder,
)
from consensus_analysis.application.services import (
    AssessImpact,
    CompareScenarios,
    ComposeCompromisePackage,
    DeriveConsensus,
    GetConsensus,
    HandleRunClosed,
    ListPackages,
    ListUnresolvedConflicts,
    RebuildProjections,
)
from consensus_analysis.domain.repositories import (
    CompromisePackageRepository,
    ConsensusRepository,
    RunLogPort,
    ScenarioRepository,
    StakeholderPowersPort,
)
from consensus_analysis.domain.values import BasisKind
from shared.config import Settings
from shared.db import Database


@dataclass(frozen=True, slots=True)
class ConsensusAnalysisContainer:
    derive_consensus: DeriveConsensus
    get_consensus: GetConsensus
    list_unresolved_conflicts: ListUnresolvedConflicts
    compose_compromise_package: ComposeCompromisePackage
    list_packages: ListPackages
    assess_impact: AssessImpact
    compare_scenarios: CompareScenarios
    rebuild_projections: RebuildProjections
    handle_run_closed: HandleRunClosed


def build_container(
    settings: Settings,
    database: Database,
    *,
    consensus: ConsensusRepository,
    packages: CompromisePackageRepository,
    scenarios: ScenarioRepository,
    log: RunLogPort,
    powers: StakeholderPowersPort,
    estimation: dict[BasisKind, EstimateStrategy],
    catalogue: IllustrativeValueSource,
    llm: LlmImpactEstimator,
    rebuilder: ProjectionRebuilder,
    ranker: ComparisonRanker,
    events: EventPublisher,
) -> ConsensusAnalysisContainer:
    """Build the container; the runtime integration issue supplies every port."""
    raise NotImplementedError("consensus-analysis composition is implemented by issue #320")
