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
    Clock,
    ComparisonRanker,
    ComponentCatalogue,
    EventPublisher,
    IdFactory,
    IllustrativeValueSource,
    LlmImpactEstimator,
    MandateThresholdSource,
    ProjectionRebuilder,
    UnitOfWork,
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
from consensus_analysis.domain.services import (
    ComponentsCompatible,
    EstimateValidator,
    FeasibilityGuard,
    IllustrativeValueGuard,
)
from consensus_analysis.domain.values import BasisKind
from shared.config import Settings
from shared.db import Database
from shared.log_setup import get_logger

logger = get_logger(__name__)


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
    mandate: MandateThresholdSource,
    estimation: dict[BasisKind, EstimateStrategy],
    catalogue: IllustrativeValueSource,
    components: ComponentCatalogue,
    llm: LlmImpactEstimator,
    rebuilder: ProjectionRebuilder,
    ranker: ComparisonRanker,
    events: EventPublisher,
    clock: Clock,
    ids: IdFactory,
    uow: UnitOfWork,
) -> ConsensusAnalysisContainer:
    """Build the container from the ports the runtime supplies.

    Nothing is defaulted here: a missing mandate threshold source, rebuild strategy or event
    publisher stops the boot rather than producing a container that cannot derive.
    """
    logger.info(
        "consensus_analysis_wired",
        persistence=settings.persistence.value,
        estimation_bases=sorted(kind.value for kind in estimation),
        note="derivation fails closed until the log, threshold and vetoes are published",
    )
    components_compatible = ComponentsCompatible()
    validator = EstimateValidator()
    illustrative = IllustrativeValueGuard()
    feasibility = FeasibilityGuard()
    derive = DeriveConsensus(
        consensus=consensus,
        log=log,
        powers=powers,
        mandate=mandate,
        rebuilder=rebuilder,
        events=events,
        clock=clock,
        ids=ids,
        uow=uow,
    )
    return ConsensusAnalysisContainer(
        derive_consensus=derive,
        get_consensus=GetConsensus(consensus=consensus),
        list_unresolved_conflicts=ListUnresolvedConflicts(consensus=consensus),
        compose_compromise_package=ComposeCompromisePackage(
            packages=packages,
            consensus=consensus,
            compatible=components_compatible,
            catalogue=components,
            events=events,
            clock=clock,
            ids=ids,
            uow=uow,
        ),
        list_packages=ListPackages(packages=packages),
        assess_impact=AssessImpact(
            packages=packages,
            scenarios=scenarios,
            estimation=estimation,
            validator=validator,
            illustrative=illustrative,
            catalogue=catalogue,
            feasibility=feasibility,
            events=events,
            ids=ids,
            uow=uow,
        ),
        compare_scenarios=CompareScenarios(
            packages=packages,
            scenarios=scenarios,
            consensus=consensus,
            ranker=ranker,
        ),
        rebuild_projections=RebuildProjections(
            consensus=consensus,
            log=log,
            powers=powers,
            rebuilder=rebuilder,
            uow=uow,
        ),
        handle_run_closed=HandleRunClosed(derive=derive),
    )
