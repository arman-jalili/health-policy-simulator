"""HTTP request/response schemas (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (API Endpoints)

These models are the OpenAPI contract. Ids are strings on the wire; decimals are strings in
proposal costs so a client can round-trip them exactly.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

StanceLiteral = Literal["support", "oppose", "qualify", "conditional_accept"]
QuantificationLiteral = Literal["quantified", "unquantified"]
OfferStatusLiteral = Literal["offered", "accepted", "declined"]
ConflictStatusLiteral = Literal["open", "resolved", "deadlocked"]


class ProposalComponentBody(BaseModel):
    measure: str = Field(min_length=1, max_length=2000)
    effect: str = Field(min_length=1, max_length=2000)
    population: str = Field(min_length=1, max_length=500)
    cost_eur: Decimal | None = Field(default=None, ge=0)
    quantification: QuantificationLiteral = "quantified"
    support_record: list[str] = Field(default_factory=list)


class ProposalBody(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    components: list[ProposalComponentBody] = Field(default_factory=list)


class OpenRunBody(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    round_cap: int | None = Field(default=None, ge=1, le=50)
    stakeholder_ids: list[str] | None = None
    consensus_threshold: float = Field(default=0.5, gt=0, le=1)


class BoundStakeholderBody(BaseModel):
    stakeholder_id: str
    institution_name: str
    institution_code: str
    profile_version: str
    persona_version: str


class OpenRunResponse(BaseModel):
    run_id: str
    phase: str
    mandate_hash: str
    bound: list[BoundStakeholderBody]


class OpenRoundBody(BaseModel):
    round: int | None = Field(default=None, ge=1)


class OpenRoundResponse(BaseModel):
    run_id: str
    round: int
    closed: bool
    turn_order: list[str]


class LearningInsightBody(BaseModel):
    insight_type: str = Field(min_length=1)
    statement: str = Field(min_length=1, max_length=5000)
    derived_from: list[str] = Field(default_factory=list)
    round_number: int = Field(default=0, ge=0)


class CloseRoundBody(BaseModel):
    learning: list[LearningInsightBody] = Field(default_factory=list)
    convergence: str = Field(default="unmeasured", max_length=64)


class RunResponse(BaseModel):
    run_id: str
    phase: str
    round: int
    round_cap: int
    closed: bool
    bound_stakeholder_ids: list[str]
    open_position_ids: list[str]
    coalition_ids: list[str]


class PositionBody(BaseModel):
    stakeholder_id: str
    topic: str
    stance: StanceLiteral
    proposal: ProposalBody
    evidence_ids: list[str] = Field(default_factory=list)


class RevisionReasonBody(BaseModel):
    argument_ids: list[str] = Field(default_factory=list)
    pack_ids: list[str] = Field(default_factory=list)
    driver: str = Field(default="", max_length=2000)


class ReviseBody(BaseModel):
    stance: StanceLiteral
    reason: RevisionReasonBody


class RevisionReasonResponse(BaseModel):
    argument_ids: list[str]
    pack_ids: list[str]
    driver: str


class PositionResponse(BaseModel):
    position_id: str
    run_id: str
    round: int
    stakeholder_id: str
    topic: str
    stance: str
    proposal: ProposalBody
    evidence_ids: list[str]
    supersedes: str | None = None
    revision: RevisionReasonResponse | None = None


class TargetBody(BaseModel):
    topic: str
    position_id: str | None = None
    argument_id: str | None = None


class ClaimBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    claim_id: str | None = None
    verdict: str | None = None


class TurnBody(BaseModel):
    stakeholder_id: str
    target: TargetBody
    stance: StanceLiteral
    text: str = Field(min_length=1, max_length=8000)
    claims: list[ClaimBody] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    unsupported: bool = False
    invocation_id: str | None = None


class ArgumentResponse(BaseModel):
    argument_id: str
    run_id: str
    round: int
    stakeholder_id: str
    target: TargetBody
    stance: str
    evidence_ids: list[str]
    unsupported: bool
    invocation_id: str | None = None


class AbstentionBody(BaseModel):
    stakeholder_id: str
    topic: str


class ConflictResponse(BaseModel):
    conflict_id: str
    run_id: str
    topic: str
    status: ConflictStatusLiteral
    stances: dict[str, str]


class ConflictListResponse(BaseModel):
    items: list[ConflictResponse]


class CoalitionOfferBody(BaseModel):
    invited_id: str
    conditions: str = ""


class CoalitionBody(BaseModel):
    topic: str
    member_ids: list[str]
    proposal: ProposalBody


class CoalitionOfferResponse(BaseModel):
    offer_id: str
    invited_id: str
    conditions: str
    status: OfferStatusLiteral
    decline_reason: str | None = None


class CoalitionResponse(BaseModel):
    coalition_id: str
    run_id: str
    topic: str
    proposal: ProposalBody
    members: list[str]
    offers: list[CoalitionOfferResponse]


class LearningInsightResponse(BaseModel):
    insight_type: str
    statement: str
    derived_from: list[str]
    round_number: int


class LearningResponse(BaseModel):
    learning_id: str
    run_id: str
    round: int
    insights: list[LearningInsightResponse]


class CloseRoundResponse(BaseModel):
    run_id: str
    round: int
    learning: LearningResponse
    stopping_condition: dict[str, object]


class LearningListResponse(BaseModel):
    items: list[LearningResponse]


class RoundResponse(BaseModel):
    round: int
    closed: bool
    argument_count: int
    abstention_count: int
    learning: LearningResponse | None = None


class RoundListResponse(BaseModel):
    items: list[RoundResponse]


class EventItem(BaseModel):
    sequence: int
    event_type: str
    payload: dict[str, object]
    occurred_at: str | None = None


class EventsResponse(BaseModel):
    items: list[EventItem]
    state: RunResponse
