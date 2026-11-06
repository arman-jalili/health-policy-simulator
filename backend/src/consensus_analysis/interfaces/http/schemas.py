"""OpenAPI schemas of the ConsensusAnalysis HTTP interface (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (API Endpoints)

Concrete FastAPI models, not interfaces: they mirror the application result DTOs for the wire, and
the field names here are the published ``/api/v1`` contract. A figure never appears without its
``basis`` and its ``label`` — that shape is the point of the endpoint, not decoration.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from consensus_analysis.domain.values import (
    BasisKind,
    ConsensusOutcomeKind,
    DerivationInputKind,
    FeasibilityLevel,
    PackageState,
    ProposalClass,
    Stance,
    UncertaintyLabel,
)


class DerivationInputBody(BaseModel):
    kind: DerivationInputKind
    reference_id: str = Field(min_length=1, max_length=200)
    description: str = ""


class EstimateBasisBody(BaseModel):
    kind: BasisKind
    inputs: list[DerivationInputBody] = Field(default_factory=list)


class EstimateLimitationBody(BaseModel):
    statement: str = Field(min_length=1, max_length=1000)
    ignored_factors: list[str] = Field(default_factory=list)


class FeasibilityRatingBody(BaseModel):
    political: FeasibilityLevel
    legal: FeasibilityLevel
    administrative: FeasibilityLevel
    basis: EstimateBasisBody
    blockers: list[str] = Field(default_factory=list)


class EstimatedFigureBody(BaseModel):
    field: str = Field(min_length=1, max_length=200)
    value: Decimal
    basis: EstimateBasisBody
    label: UncertaintyLabel
    limitation: EstimateLimitationBody | None = None


class MinorityBody(BaseModel):
    holders: list[str] = Field(min_length=1)
    objections: list[str] = Field(default_factory=list)


class ConsensusRecordBody(BaseModel):
    consensus_id: str
    run_id: str
    topic: str
    proposal_class: ProposalClass
    outcome: ConsensusOutcomeKind
    support: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(gt=0.0, le=1.0)
    supporters: list[str] = Field(default_factory=list)
    minorities: list[MinorityBody] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class ConsensusResponse(BaseModel):
    records: list[ConsensusRecordBody] = Field(default_factory=list)


class DeriveBody(BaseModel):
    topics: list[str] = Field(default_factory=list)


class StancePositionBody(BaseModel):
    stakeholder: str
    stance: Stance
    weight: float = Field(ge=0.0, le=1.0)
    recorded: bool
    log_position: int | None = None


class UnresolvedConflictBody(BaseModel):
    topic: str
    positions: list[StancePositionBody] = Field(min_length=2)


class UnresolvedConflictListResponse(BaseModel):
    conflicts: list[UnresolvedConflictBody] = Field(default_factory=list)


class ComposePackageBody(BaseModel):
    component_ids: list[str] = Field(default_factory=list)
    rejected_ids: list[str] = Field(default_factory=list)


class ComposePackageResponse(BaseModel):
    package_id: str
    component_ids: list[str] = Field(default_factory=list)
    rejected_count: int = Field(ge=0)
    state: PackageState


class PackageSummaryBody(BaseModel):
    package_id: str
    state: PackageState
    component_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)


class PackageListResponse(BaseModel):
    packages: list[PackageSummaryBody] = Field(default_factory=list)


class BaselineBody(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    reference: str = ""


class HorizonBody(BaseModel):
    years: int = Field(ge=1, le=50)
    description: str = ""


class AssumptionBody(BaseModel):
    statement: str = Field(min_length=1, max_length=1000)
    basis: EstimateBasisBody


class AssessImpactBody(BaseModel):
    baseline: BaselineBody
    horizon: HorizonBody
    assumptions: list[AssumptionBody] = Field(default_factory=list)


class AssessImpactResponse(BaseModel):
    scenario_id: str
    package_id: str
    figures: list[EstimatedFigureBody] = Field(default_factory=list)
    feasibility: FeasibilityRatingBody | None = None


class ComparisonEntryBody(BaseModel):
    """One ranked alternative. Cost, acceptance and feasibility are all mandatory."""

    package_id: str
    scenario_id: str
    cost: Decimal | None = None
    acceptance: float = Field(ge=0.0, le=1.0)
    feasibility: FeasibilityRatingBody
    rank: int = Field(ge=1)


class ComparisonResponse(BaseModel):
    entries: list[ComparisonEntryBody] = Field(default_factory=list)
