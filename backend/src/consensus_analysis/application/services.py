"""Frozen application services of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Service classification, API)

Constructors, service names and ``execute`` signatures are frozen. Bodies raise
``NotImplementedError`` naming the implementing issue; later issues may not rename or remove a
frozen member without a new freeze entry.

``collaborators`` is the published wiring contract of each use case: it names every port the
composition root must supply, and it is what keeps the W8 reachability gate honest while the bodies
are still stubs. Implementing issues replace it with real call sites.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from consensus_analysis.application.commands import (
    AssessImpactRequest,
    CompareScenariosRequest,
    ComposeCompromisePackageRequest,
    DeriveConsensusRequest,
    GetConsensusRequest,
    ListPackagesRequest,
    ListUnresolvedConflictsRequest,
    RebuildProjectionsRequest,
    RunClosedRequest,
)
from consensus_analysis.application.dto import (
    ComparisonResult,
    ComposePackageResult,
    ConsensusResult,
    PackageListResult,
    RebuildResult,
    RunClosedResult,
    ScenarioResult,
    UnresolvedConflictListResult,
)
from consensus_analysis.application.estimators import EstimateStrategy
from consensus_analysis.application.ports import (
    Clock,
    ComparisonRanker,
    EventPublisher,
    IdFactory,
    IllustrativeValueSource,
    ProjectionRebuilder,
    UnitOfWork,
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

SERVICE_CLASSIFICATION: Mapping[str, str] = MappingProxyType(
    {
        "DeriveConsensus": "application",
        "GetConsensus": "application",
        "ListUnresolvedConflicts": "application",
        "ComposeCompromisePackage": "application",
        "ListPackages": "application",
        "AssessImpact": "application",
        "CompareScenarios": "application",
        "RebuildProjections": "application",
        "HandleRunClosed": "application",
        "ConsensusRule": "domain",
        "NotVetoed": "domain",
        "ThresholdMet": "domain",
        "MajorityHolds": "domain",
        "MinorityCapture": "domain",
        "ComponentsCompatible": "domain",
        "EstimateValidator": "domain",
        "IllustrativeValueGuard": "domain",
        "FeasibilityGuard": "domain",
        "ProjectionRebuilder": "infrastructure",
    }
)
"""Where every service of this context belongs.

Machine-checked by ``tests/unit/consensus-analysis/service-classification``: every entry resolves to
a class living in the named layer, so the classification cannot drift into a comment. The rebuild
strategy is the single ``infrastructure`` entry: a port consumed here, implemented there.
"""


class DeriveConsensus:
    """Read the closed run log, evaluate the rules and persist the derived records (AC 1, 2, 3)."""

    def __init__(
        self,
        *,
        consensus: ConsensusRepository,
        log: RunLogPort,
        powers: StakeholderPowersPort,
        events: EventPublisher,
        clock: Clock,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._consensus = consensus
        self._log = log
        self._powers = powers
        self._events = events
        self._clock = clock
        self._ids = ids
        self._uow = uow

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (
            self._consensus,
            self._log,
            self._powers,
            self._events,
            self._clock,
            self._ids,
            self._uow,
        )

    async def execute(self, request: DeriveConsensusRequest) -> ConsensusResult:
        raise NotImplementedError("DeriveConsensus.execute is implemented by issue #306")


class GetConsensus:
    """Read the persisted projection of one run; it never recomputes (invariant 1)."""

    def __init__(self, *, consensus: ConsensusRepository) -> None:
        self._consensus = consensus

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._consensus,)

    async def execute(self, request: GetConsensusRequest) -> ConsensusResult:
        raise NotImplementedError("GetConsensus.execute is implemented by issue #306")


class ListUnresolvedConflicts:
    """List the conflicts that are still open at run close, with their positions."""

    def __init__(self, *, consensus: ConsensusRepository) -> None:
        self._consensus = consensus

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._consensus,)

    async def execute(
        self, request: ListUnresolvedConflictsRequest
    ) -> UnresolvedConflictListResult:
        raise NotImplementedError("ListUnresolvedConflicts.execute is implemented by issue #306")


class ComposeCompromisePackage:
    """Transaction boundary for package assembly; documents every rejected proposal (AC 9)."""

    def __init__(
        self,
        *,
        packages: CompromisePackageRepository,
        consensus: ConsensusRepository,
        compatible: ComponentsCompatible,
        events: EventPublisher,
        clock: Clock,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._packages = packages
        self._consensus = consensus
        self._compatible = compatible
        self._events = events
        self._clock = clock
        self._ids = ids
        self._uow = uow

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (
            self._packages,
            self._consensus,
            self._compatible,
            self._events,
            self._clock,
            self._ids,
            self._uow,
        )

    async def execute(self, request: ComposeCompromisePackageRequest) -> ComposePackageResult:
        raise NotImplementedError("ComposeCompromisePackage.execute is implemented by issue #317")


class ListPackages:
    """List the composed packages of a run with their provenance counters."""

    def __init__(self, *, packages: CompromisePackageRepository) -> None:
        self._packages = packages

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._packages,)

    async def execute(self, request: ListPackagesRequest) -> PackageListResult:
        raise NotImplementedError("ListPackages.execute is implemented by issue #317")


class AssessImpact:
    """Estimate a scenario's impacts and refuse any figure that cannot prove its basis (AC 5-7)."""

    def __init__(
        self,
        *,
        packages: CompromisePackageRepository,
        scenarios: ScenarioRepository,
        estimation: Mapping[BasisKind, EstimateStrategy],
        validator: EstimateValidator,
        illustrative: IllustrativeValueGuard,
        catalogue: IllustrativeValueSource,
        feasibility: FeasibilityGuard,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._packages = packages
        self._scenarios = scenarios
        self._estimation = estimation
        self._validator = validator
        self._illustrative = illustrative
        self._catalogue = catalogue
        self._feasibility = feasibility
        self._events = events
        self._ids = ids
        self._uow = uow

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (
            self._packages,
            self._scenarios,
            self._estimation,
            self._validator,
            self._illustrative,
            self._catalogue,
            self._feasibility,
            self._events,
            self._ids,
            self._uow,
        )

    async def execute(self, request: AssessImpactRequest) -> ScenarioResult:
        raise NotImplementedError("AssessImpact.execute is implemented by issue #313")


class CompareScenarios:
    """Rank alternatives on cost, acceptance and feasibility; all three are mandatory (AC 11)."""

    def __init__(
        self,
        *,
        packages: CompromisePackageRepository,
        scenarios: ScenarioRepository,
        consensus: ConsensusRepository,
        ranker: ComparisonRanker,
    ) -> None:
        self._packages = packages
        self._scenarios = scenarios
        self._consensus = consensus
        self._ranker = ranker

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._packages, self._scenarios, self._consensus, self._ranker)

    async def execute(self, request: CompareScenariosRequest) -> ComparisonResult:
        raise NotImplementedError("CompareScenarios.execute is implemented by issue #319")


class RebuildProjections:
    """Operator command: replay the log and prove the rows are reproduced (AC 4)."""

    def __init__(
        self,
        *,
        consensus: ConsensusRepository,
        log: RunLogPort,
        powers: StakeholderPowersPort,
        rebuilder: ProjectionRebuilder,
        uow: UnitOfWork,
    ) -> None:
        self._consensus = consensus
        self._log = log
        self._powers = powers
        self._rebuilder = rebuilder
        self._uow = uow

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._consensus, self._log, self._powers, self._rebuilder, self._uow)

    async def execute(self, request: RebuildProjectionsRequest) -> RebuildResult:
        raise NotImplementedError("RebuildProjections.execute is implemented by issue #312")


class HandleRunClosed:
    """Subscribed entry point: a closed run derives its consensus rows with no API call (AC 12)."""

    def __init__(self, *, derive: DeriveConsensus) -> None:
        self._derive = derive

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._derive,)

    async def execute(self, request: RunClosedRequest) -> RunClosedResult:
        raise NotImplementedError("HandleRunClosed.execute is implemented by issue #320")
