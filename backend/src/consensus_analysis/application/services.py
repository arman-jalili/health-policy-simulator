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

import hashlib
from collections.abc import Mapping, Sequence
from decimal import Decimal
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
    ComparisonEntryResult,
    ComparisonResult,
    ComposePackageResult,
    ConsensusResult,
    EstimatedFigureResult,
    EstimateRequest,
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
    ComponentCatalogue,
    EventPublisher,
    IdFactory,
    IllustrativeValueSource,
    ProjectionRebuilder,
    UnitOfWork,
)
from consensus_analysis.domain.compromise_package import CompromisePackage
from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.entities import ImpactAssessment, RejectedProposal
from consensus_analysis.domain.errors import (
    CompromisePackageNotFound,
    ConsensusAnalysisUnavailable,
    IncompatibleComponent,
    IncompleteComparison,
    ProjectionRebuildFailed,
    UnbackedEstimate,
)
from consensus_analysis.domain.events import UnbackedEstimateBlocked
from consensus_analysis.domain.repositories import (
    CompromisePackageRepository,
    ConsensusRepository,
    RunLogPort,
    ScenarioRepository,
    StakeholderPowersPort,
)
from consensus_analysis.domain.scenario import Scenario
from consensus_analysis.domain.services import (
    ComponentsCompatible,
    EstimateValidator,
    FeasibilityGuard,
    IllustrativeValueGuard,
)
from consensus_analysis.domain.values import (
    AssessmentId,
    BasisKind,
    ComparisonDimension,
    EstimatedFigure,
    LogPosition,
    PackageId,
    RejectedProposalId,
    ScenarioId,
    SupportLevel,
)

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
        catalogue: ComponentCatalogue,
        events: EventPublisher,
        clock: Clock,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._packages = packages
        self._consensus = consensus
        self._compatible = compatible
        self._catalogue = catalogue
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
            self._catalogue,
            self._events,
            self._clock,
            self._ids,
            self._uow,
        )

    async def execute(self, request: ComposeCompromisePackageRequest) -> ComposePackageResult:
        """Combine the individually accepted, mutually compatible components (AC 9).

        A component that is not in the run's accepted catalogue cannot enter the bundle: composing
        around a part nobody accepted is the failure invariant 5 exists to stop.
        """
        catalogue = {
            str(component.id): component
            for component in await self._catalogue.components(request.run_id)
        }
        unknown = [str(item) for item in request.component_ids if str(item) not in catalogue]
        if unknown:
            raise IncompatibleComponent(
                f"components were not individually accepted: {', '.join(sorted(unknown))}",
                details=[{"message": "not accepted", "field": item} for item in sorted(unknown)],
            )
        package = CompromisePackage.open(
            package_id=PackageId(self._ids.new_id("pkg")),
            run_id=request.run_id,
            log_position=LogPosition(0),
        )
        for component_id in request.component_ids:
            package.add_component(catalogue[str(component_id)])
        package.compose(
            rejected=tuple(
                RejectedProposal(
                    id=RejectedProposalId(self._ids.new_id("rjp")),
                    measure=str(component_id),
                    support=SupportLevel(value=0.0),
                    reason="did not reach the mandate threshold",
                )
                for component_id in request.rejected_ids
            )
        )
        async with self._uow.transaction():
            await self._packages.save(package)
            await self._events.publish(package.drain_events())
        return ComposePackageResult(
            package_id=package.id,
            component_ids=package.component_ids(),
            rejected_count=len(package.rejected_proposals),
            state=package.state,
        )


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
        """Define the scenario, estimate every assumption and refuse an unbacked figure (AC 5).

        A refused figure is published as ``UnbackedEstimateBlocked`` *before* the transaction
        aborts: the refusal is the auditable fact, so losing it because the write rolled back would
        hide exactly what this guard exists to record.
        """
        package = await self._packages.get(request.package_id)
        if package is None:
            raise CompromisePackageNotFound(f"package {request.package_id} not found")
        scenario = Scenario.define(
            scenario_id=ScenarioId(self._ids.new_id("scn")),
            package_id=package.id,
            baseline=request.baseline,
            horizon=request.horizon,
            log_position=package.log_position,
            assumptions=request.assumptions,
        )
        figures: list[EstimatedFigure] = []
        for assumption in request.assumptions:
            strategy = self._estimation.get(assumption.basis.kind)
            if strategy is None:
                raise ConsensusAnalysisUnavailable(
                    f"no estimation strategy registered for basis {assumption.basis.kind.value!r}"
                )
            figure = await strategy.estimate(
                EstimateRequest(
                    scenario_id=scenario.id,
                    field=assumption.statement,
                    inputs=assumption.basis.inputs,
                )
            )
            try:
                self._validator.validate(figure)
            except UnbackedEstimate:
                await self._events.publish(
                    (
                        UnbackedEstimateBlocked(
                            scenario_id=scenario.id,
                            field=figure.field,
                            claimed_basis=figure.basis.kind,
                        ),
                    )
                )
                raise
            self._illustrative.refuse(figure, self._catalogue.examples())
            figures.append(figure)
        assessment = ImpactAssessment.assess(
            assessment_id=AssessmentId(self._ids.new_id("imp")),
            scenario_id=scenario.id,
            package_id=package.id,
            figures=tuple(figures),
        )
        scenario.assess(assessment)
        async with self._uow.transaction():
            await self._scenarios.save(scenario)
            await self._events.publish(scenario.drain_events())
        return ScenarioResult(
            scenario_id=scenario.id,
            package_id=package.id,
            figures=tuple(
                EstimatedFigureResult(
                    field=figure.field,
                    value=figure.value,
                    basis=figure.basis,
                    label=figure.label,
                    limitation=figure.limitation,
                )
                for figure in figures
            ),
            feasibility=assessment.feasibility,
        )


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
        """Rank the package's alternatives with all three dimensions present (AC 11).

        An alternative that cannot supply cost or feasibility is refused rather than ranked on the
        dimensions it happens to have: a partially ranked comparison reads as a verdict on the
        dimensions it omitted.
        """
        package = await self._packages.get(request.package_id)
        if package is None:
            raise CompromisePackageNotFound(f"package {request.package_id} not found")
        scenarios = await self._scenarios.for_package(package.id)
        records = await self._consensus.for_run(package.run_id)
        acceptance = min(
            (record.outcome.support.value for record in records if record.outcome is not None),
            default=0.0,
        )
        cost = _package_cost(package)
        entries: list[ComparisonEntryResult] = []
        for scenario in scenarios:
            feasibility = scenario.assessments[-1].feasibility if scenario.assessments else None
            missing = [
                dimension.value
                for dimension, present in (
                    (ComparisonDimension.COST, cost is not None),
                    (ComparisonDimension.FEASIBILITY, feasibility is not None),
                )
                if not present
            ]
            if missing or feasibility is None or cost is None:
                raise IncompleteComparison(str(package.id), missing)
            entries.append(
                ComparisonEntryResult(
                    package_id=package.id,
                    scenario_id=scenario.id,
                    cost=cost,
                    acceptance=acceptance,
                    feasibility=feasibility,
                    rank=1,
                )
            )
        return ComparisonResult(entries=tuple(self._ranker.rank(entries)))


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
        """Replay the log and prove the persisted rows are reproduced (AC 4).

        The command verifies what exists rather than inventing a projection: with no rows there is
        nothing to reproduce, and rows disagreeing on their mandate threshold cannot come from one
        mandate. Both are reported instead of being silently overwritten.
        """
        persisted = await self._consensus.for_run(request.run_id)
        if not persisted:
            raise ProjectionRebuildFailed(
                f"run {request.run_id} has no projection rows to reproduce"
            )
        shares = {round(row.threshold.required_share, 12) for row in persisted}
        if len(shares) != 1:
            raise ProjectionRebuildFailed(
                f"run {request.run_id} holds {len(shares)} mandate thresholds; "
                "one run carries one mandate"
            )
        agenda = await self._log.agenda(request.run_id)
        stances = await self._log.stances(request.run_id)
        stakeholders = sorted(
            {snapshot.stakeholder for row in persisted for snapshot in row.ordered_stances()},
            key=str,
        )
        vetoes = await self._powers.veto_classes(stakeholders)
        rebuilt = tuple(
            await self._rebuilder.rebuild(
                run_id=request.run_id,
                agenda=agenda,
                stances=stances,
                vetoes=vetoes,
                threshold=persisted[0].threshold,
            )
        )
        drift = _projection_drift(persisted, rebuilt)
        if drift:
            raise ProjectionRebuildFailed(
                "replayed rows differ from the persisted projection: " + "; ".join(drift),
                details=[{"message": message} for message in drift],
            )
        if not request.verify_only:
            async with self._uow.transaction():
                await self._consensus.replace_for_run(request.run_id, rebuilt)
        return RebuildResult(
            run_id=request.run_id,
            records=len(rebuilt),
            digest=_combined_digest(rebuilt),
        )


class HandleRunClosed:
    """Subscribed entry point: a closed run derives its consensus rows with no API call (AC 12)."""

    def __init__(self, *, derive: DeriveConsensus) -> None:
        self._derive = derive

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._derive,)

    async def execute(self, request: RunClosedRequest) -> RunClosedResult:
        raise NotImplementedError("HandleRunClosed.execute is implemented by issue #320")


def _projection_drift(
    persisted: Sequence[ConsensusRecord], rebuilt: Sequence[ConsensusRecord]
) -> list[str]:
    """Return every difference between the stored rows and a fresh replay, by topic."""
    stored = {row.topic: row.digest() for row in persisted}
    replayed = {row.topic: row.digest() for row in rebuilt}
    drift: list[str] = []
    for topic in sorted(set(stored) | set(replayed), key=str):
        if topic not in replayed:
            drift.append(f"{topic}: persisted but not reproducible from the log")
        elif topic not in stored:
            drift.append(f"{topic}: reproducible from the log but missing from the projection")
        elif stored[topic] != replayed[topic]:
            drift.append(f"{topic}: replayed content differs")
    return drift


def _combined_digest(records: Sequence[ConsensusRecord]) -> str:
    """One hash over the whole rebuild, so a caller can compare two rebuilds in a word."""
    joined = "\n".join(f"{row.topic}:{row.digest()}" for row in records)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _package_cost(package: CompromisePackage) -> Decimal | None:
    """Total declared cost of the package, or ``None`` when a component left it unquantified."""
    if not package.components:
        return None
    if any(component.cost_eur is None for component in package.components):
        return None
    return sum(
        (component.cost_eur for component in package.components if component.cost_eur is not None),
        Decimal("0"),
    )
