"""ConsensusAnalysis HTTP router — the wired API surface (ADR-004, issue #321).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (API Endpoints)

Routes, scopes, payload shapes and error envelopes are the contract; every handler delegates to a
use case in the container and does no business work of its own. Keeping the router concrete (no
separate handler interface) is deliberate — controllers are not interfaces.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from consensus_analysis.application.commands import (
    AssessImpactRequest,
    CompareScenariosRequest,
    ComposeCompromisePackageRequest,
    DeriveConsensusRequest,
    GetConsensusRequest,
    ListPackagesRequest,
    ListUnresolvedConflictsRequest,
)
from consensus_analysis.application.dto import ConsensusRecordResult, MinorityResult
from consensus_analysis.domain.values import (
    BaselineRef,
    ComponentId,
    DerivationInput,
    EstimateBasis,
    Horizon,
    PackageId,
    RunId,
    ScenarioAssumption,
    TopicRef,
)
from consensus_analysis.interfaces.http.deps import ConsensusAnalysisContainer, get_container
from consensus_analysis.interfaces.http.schemas import (
    AssessImpactBody,
    AssessImpactResponse,
    ComparisonEntryBody,
    ComparisonResponse,
    ComposePackageBody,
    ComposePackageResponse,
    ConsensusRecordBody,
    ConsensusResponse,
    DerivationInputBody,
    DeriveBody,
    EstimateBasisBody,
    EstimatedFigureBody,
    EstimateLimitationBody,
    FeasibilityRatingBody,
    MinorityBody,
    PackageListResponse,
    PackageSummaryBody,
    StancePositionBody,
    UnresolvedConflictBody,
    UnresolvedConflictListResponse,
)
from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["consensus-analysis"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)


@router.post(
    "/runs/{run_id}/analysis:derive",
    response_model=ConsensusResponse,
    summary="Derive the consensus records of a closed run",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def derive_consensus(
    run_id: str,
    body: DeriveBody,
    container: Annotated[ConsensusAnalysisContainer, Depends(get_container)],
) -> ConsensusResponse:
    """Derive every topic outcome from the closed run log; never assume agreement."""
    result = await container.derive_consensus.execute(
        DeriveConsensusRequest(
            run_id=RunId(run_id), topics=tuple(TopicRef(topic) for topic in body.topics)
        )
    )
    return ConsensusResponse(records=[_record_body(record) for record in result.records])


@router.get(
    "/runs/{run_id}/consensus",
    response_model=ConsensusResponse,
    summary="Read the derived consensus records with majority and minority",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_consensus(
    run_id: str,
    container: Annotated[ConsensusAnalysisContainer, Depends(get_container)],
) -> ConsensusResponse:
    """Return the persisted projection; the read never recomputes the outcome."""
    result = await container.get_consensus.execute(GetConsensusRequest(run_id=RunId(run_id)))
    return ConsensusResponse(records=[_record_body(record) for record in result.records])


@router.get(
    "/runs/{run_id}/conflicts/open",
    response_model=UnresolvedConflictListResponse,
    summary="List the conflicts still open at run close",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_unresolved_conflicts(
    run_id: str,
    container: Annotated[ConsensusAnalysisContainer, Depends(get_container)],
) -> UnresolvedConflictListResponse:
    """Return every unresolved conflict together with the positions that remain apart."""
    result = await container.list_unresolved_conflicts.execute(
        ListUnresolvedConflictsRequest(run_id=RunId(run_id))
    )
    return UnresolvedConflictListResponse(
        conflicts=[
            UnresolvedConflictBody(
                topic=str(conflict.topic),
                positions=[
                    StancePositionBody(
                        stakeholder=str(position.stakeholder),
                        stance=position.stance,
                        weight=position.weight,
                        recorded=position.recorded,
                        log_position=(
                            int(position.log_position) if position.log_position else None
                        ),
                    )
                    for position in conflict.positions
                ],
            )
            for conflict in result.conflicts
        ]
    )


@router.post(
    "/runs/{run_id}/packages",
    response_model=ComposePackageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compose a compromise package from accepted components",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def compose_compromise_package(
    run_id: str,
    body: ComposePackageBody,
    container: Annotated[ConsensusAnalysisContainer, Depends(get_container)],
) -> ComposePackageResponse:
    """Combine individually accepted, compatible components and document every rejection."""
    result = await container.compose_compromise_package.execute(
        ComposeCompromisePackageRequest(
            run_id=RunId(run_id),
            component_ids=tuple(ComponentId(item) for item in body.component_ids),
            rejected_ids=tuple(ComponentId(item) for item in body.rejected_ids),
        )
    )
    return ComposePackageResponse(
        package_id=str(result.package_id),
        component_ids=[str(item) for item in result.component_ids],
        rejected_count=result.rejected_count,
        state=result.state,
    )


@router.get(
    "/runs/{run_id}/packages",
    response_model=PackageListResponse,
    summary="List composed packages with their provenance counters",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_packages(
    run_id: str,
    container: Annotated[ConsensusAnalysisContainer, Depends(get_container)],
) -> PackageListResponse:
    """Return the packages of one run with accepted and rejected counts."""
    result = await container.list_packages.execute(ListPackagesRequest(run_id=RunId(run_id)))
    return PackageListResponse(
        packages=[
            PackageSummaryBody(
                package_id=str(package.package_id),
                state=package.state,
                component_count=package.component_count,
                rejected_count=package.rejected_count,
            )
            for package in result.packages
        ]
    )


@router.post(
    "/packages/{package_id}/scenarios",
    response_model=AssessImpactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Define and assess a scenario against a package",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def assess_impact(
    package_id: str,
    body: AssessImpactBody,
    container: Annotated[ConsensusAnalysisContainer, Depends(get_container)],
) -> AssessImpactResponse:
    """Estimate the impacts, refusing any figure that cannot prove its basis."""
    result = await container.assess_impact.execute(
        AssessImpactRequest(
            package_id=PackageId(package_id),
            baseline=BaselineRef(label=body.baseline.label, reference=body.baseline.reference),
            horizon=Horizon(years=body.horizon.years, description=body.horizon.description),
            assumptions=tuple(
                ScenarioAssumption(
                    statement=item.statement,
                    basis=EstimateBasis(
                        kind=item.basis.kind,
                        inputs=tuple(
                            DerivationInput(
                                kind=entry.kind,
                                reference_id=entry.reference_id,
                                description=entry.description,
                            )
                            for entry in item.basis.inputs
                        ),
                    ),
                )
                for item in body.assumptions
            ),
        )
    )
    return AssessImpactResponse(
        scenario_id=str(result.scenario_id),
        package_id=str(result.package_id),
        figures=[
            EstimatedFigureBody(
                field=figure.field,
                value=figure.value,
                basis=EstimateBasisBody(
                    kind=figure.basis.kind,
                    inputs=[
                        DerivationInputBody(
                            kind=item.kind,
                            reference_id=item.reference_id,
                            description=item.description,
                        )
                        for item in figure.basis.inputs
                    ],
                ),
                label=figure.label,
                limitation=(
                    EstimateLimitationBody(
                        statement=figure.limitation.statement,
                        ignored_factors=list(figure.limitation.ignored_factors),
                    )
                    if figure.limitation is not None
                    else None
                ),
            )
            for figure in result.figures
        ],
        feasibility=_feasibility_body(result),
    )


@router.get(
    "/packages/{package_id}/comparison",
    response_model=ComparisonResponse,
    summary="Rank alternative packages on cost, acceptance and feasibility",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def compare_scenarios(
    package_id: str,
    container: Annotated[ConsensusAnalysisContainer, Depends(get_container)],
) -> ComparisonResponse:
    """Return ranked alternatives; a comparison missing a dimension is invalid."""
    result = await container.compare_scenarios.execute(
        CompareScenariosRequest(package_id=PackageId(package_id))
    )
    return ComparisonResponse(
        entries=[
            ComparisonEntryBody(
                package_id=str(entry.package_id),
                scenario_id=str(entry.scenario_id),
                cost=entry.cost,
                acceptance=entry.acceptance,
                feasibility=FeasibilityRatingBody(
                    political=entry.feasibility.political,
                    legal=entry.feasibility.legal,
                    administrative=entry.feasibility.administrative,
                    basis=EstimateBasisBody(
                        kind=entry.feasibility.basis.kind,
                        inputs=[
                            DerivationInputBody(
                                kind=item.kind,
                                reference_id=item.reference_id,
                                description=item.description,
                            )
                            for item in entry.feasibility.basis.inputs
                        ],
                    ),
                    blockers=[str(item) for item in entry.feasibility.blockers],
                ),
                rank=entry.rank,
            )
            for entry in result.entries
        ]
    )


def _record_body(record: ConsensusRecordResult) -> ConsensusRecordBody:
    return ConsensusRecordBody(
        consensus_id=str(record.consensus_id),
        run_id=str(record.run_id),
        topic=str(record.topic),
        proposal_class=record.proposal_class,
        outcome=record.outcome,
        support=record.support,
        threshold=record.threshold,
        supporters=[str(item) for item in record.supporters],
        minorities=[_minority_body(item) for item in record.minorities],
        blockers=[str(item) for item in record.blockers],
    )


def _minority_body(minority: MinorityResult) -> MinorityBody:
    return MinorityBody(
        holders=[str(item) for item in minority.holders],
        objections=list(minority.objections),
    )


def _feasibility_body(result: object) -> FeasibilityRatingBody | None:
    rating = getattr(result, "feasibility", None)
    if rating is None:
        return None
    return FeasibilityRatingBody(
        political=rating.political,
        legal=rating.legal,
        administrative=rating.administrative,
        basis=EstimateBasisBody(
            kind=rating.basis.kind,
            inputs=[
                DerivationInputBody(
                    kind=item.kind,
                    reference_id=item.reference_id,
                    description=item.description,
                )
                for item in rating.basis.inputs
            ],
        ),
        blockers=[str(item) for item in rating.blockers],
    )
