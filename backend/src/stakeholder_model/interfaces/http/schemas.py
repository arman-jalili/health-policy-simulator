"""OpenAPI schemas of the StakeholderModel HTTP interface (ADR-004).

Canonical: .pi/architecture/modules/stakeholder-model.md

Concrete FastAPI models, not interfaces: they mirror the application DTOs for the wire. Field names
here are the published API contract — renaming one is a breaking change for ``/api/v1``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from stakeholder_model.domain.values import (
    AttributionStrength,
    BudgetPeriod,
    InstitutionCategory,
    PowerSourceKind,
    ProposalClass,
)


class InstitutionBody(BaseModel):
    name: str
    short_name: str
    category: InstitutionCategory
    code: str


class MandateSourceBody(BaseModel):
    kind: PowerSourceKind
    citation: str
    as_of: date


class MandateScopeBody(BaseModel):
    topics: list[str] = Field(min_length=1)
    description: str
    source: MandateSourceBody


class InterestBody(BaseModel):
    topic: str
    goal: str
    weight: float = Field(ge=0.0, le=1.0)


class ConstraintBody(BaseModel):
    statement: str
    topic: str


class BudgetBody(BaseModel):
    amount_eur: Decimal
    period: BudgetPeriod
    tolerance: float = Field(ge=0.0, le=1.0)
    source: MandateSourceBody


class PriorityBody(BaseModel):
    rank: int = Field(ge=1)
    topic: str


class VetoRightBody(BaseModel):
    proposal_class: ProposalClass
    source: MandateSourceBody


class RegisterStakeholderBody(BaseModel):
    identity: InstitutionBody
    mandate_scope: MandateScopeBody
    budget: BudgetBody
    interests: list[InterestBody]
    constraints: list[ConstraintBody]
    priorities: list[PriorityBody] = Field(default_factory=list)
    veto_rights: list[VetoRightBody] = Field(default_factory=list)


class RegisterStakeholderResponse(BaseModel):
    stakeholder_id: str
    profile_version: str


class StakeholderSummaryResponse(BaseModel):
    stakeholder_id: str
    identity: InstitutionBody
    interest_count: int
    constraint_count: int
    profile_version: str


class StakeholdersResponse(BaseModel):
    items: list[StakeholderSummaryResponse]


class BudgetResponse(BudgetBody):
    pass


class MandateScopeResponse(MandateScopeBody):
    pass


class VetoRightResponse(VetoRightBody):
    pass


class PositionResponse(BaseModel):
    position_id: str
    stakeholder_id: str
    stance: str
    attribution: AttributionStrength
    stated_on: date
    passage_id: str
    usable: bool


class StakeholderProfileResponse(BaseModel):
    stakeholder_id: str
    identity: InstitutionBody
    mandate_scope: MandateScopeResponse
    budget: BudgetResponse
    interests: list[InterestBody]
    constraints: list[ConstraintBody]
    priorities: list[PriorityBody]
    red_lines: list[str]
    veto_rights: list[VetoRightResponse]
    positions: list[PositionResponse]
    profile_version: str


class UpdateProfileBody(BaseModel):
    interests: list[InterestBody] | None = None
    constraints: list[ConstraintBody] | None = None
    priorities: list[PriorityBody] | None = None
    red_lines: list[str] | None = None
    expected_version: str | None = None


class UpdateProfileResponse(BaseModel):
    stakeholder_id: str
    profile_version: str
    changed_fields: list[str]


class CitePowerSourceBody(BaseModel):
    power_type: str
    proposal_class: ProposalClass | None = None
    citation: str
    kind: PowerSourceKind
    as_of: date


class CitePowerSourceResponse(BaseModel):
    accepted: bool
    reason: str | None = None


class HistoricalPositionBody(BaseModel):
    stance: str
    attribution: AttributionStrength
    stated_on: date
    passage_id: str


class HistoricalPositionsResponse(BaseModel):
    stakeholder_id: str
    positions: list[PositionResponse]


class SelectionBody(BaseModel):
    mandate: str


class SelectionItem(BaseModel):
    stakeholder_id: str
    materiality: float = Field(ge=0.0, le=1.0)


class SelectionResponse(BaseModel):
    items: list[SelectionItem]


class BindBody(BaseModel):
    stakeholder_ids: list[str] = Field(min_length=1)


class BindingResponse(BaseModel):
    binding_id: str
    stakeholder_id: str
    persona_version: str


class BindResponse(BaseModel):
    bindings: list[BindingResponse]
