"""HTTP request/response schemas of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (API Endpoints)

These models are the published wire contract (AC 3). Field names and types are frozen; the brief
document always carries the disclaimer and the model/prompt version reference (AC 10).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from decision_brief.interfaces.renderer import BRIEF_DOCUMENT_SCHEMA_VERSION


class CitationBody(BaseModel):
    """One citation with its resolution state and, when resolved, its locator."""

    passage_id: str
    resolved: bool
    quote: str | None = None
    outlet: str | None = None
    published_on: date | None = None
    medium: str | None = None
    page_from: int | None = Field(default=None, ge=1)
    page_to: int | None = Field(default=None, ge=1)
    source_uri: str | None = None


class CitedStatementBody(BaseModel):
    text: str
    status: Literal["evidenced", "narrative", "unsupported"]
    claim_ids: list[str] = Field(default_factory=list)
    citations: list[CitationBody] = Field(default_factory=list)


class BriefSectionBody(BaseModel):
    kind: str
    ordinal: int = Field(ge=1, le=8)
    statements: list[CitedStatementBody] = Field(default_factory=list)


class RejectedProposalBody(BaseModel):
    measure: str
    blocking_stakeholders: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class DisclaimerBody(BaseModel):
    """Mandated probabilistic disclosure plus the pinned model/prompt reference (AC 10)."""

    text: str = Field(min_length=1)
    model_reference: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)


class TopicOutcomeBody(BaseModel):
    """A topic rendered honestly: recommendation, blocked or still disputed (AC 9)."""

    topic: str
    kind: Literal["recommendation", "blocked", "open_dispute"]
    blocking_stakeholders: list[str] = Field(default_factory=list)
    reason: str | None = None


class BriefVersionBody(BaseModel):
    number: int = Field(ge=1)
    run_id: str
    snapshot_ref: str
    generated_at: datetime
    previous_version: int | None = Field(default=None, ge=1)
    reason: str | None = None


class BriefResponse(BaseModel):
    """The frozen brief document returned by publication and by every read."""

    brief_id: str
    run_id: str
    status: str
    version: BriefVersionBody
    sections: list[BriefSectionBody]
    rejected_proposals: list[RejectedProposalBody] = Field(default_factory=list)
    outcomes: list[TopicOutcomeBody] = Field(default_factory=list)
    disclaimer: DisclaimerBody
    citation_count: int = Field(ge=0)
    schema_version: str = BRIEF_DOCUMENT_SCHEMA_VERSION


class VersionBriefBody(BaseModel):
    """A successor version needs a stated reason; an empty reason is not lineage."""

    reason: str = Field(min_length=1)


class VersionBriefResponse(BaseModel):
    brief_id: str
    previous_version: int = Field(ge=1)
    version: int = Field(ge=2)
    reason: str


class BriefVersionSummary(BaseModel):
    brief_id: str
    version: int = Field(ge=1)
    previous_version: int | None = Field(default=None, ge=1)
    reason: str | None = None
    status: str
    generated_at: datetime


class BriefVersionListResponse(BaseModel):
    run_id: str
    versions: list[BriefVersionSummary] = Field(default_factory=list)


class CitationListResponse(BaseModel):
    brief_id: str
    section: str | None = None
    items: list[CitationBody] = Field(default_factory=list)
