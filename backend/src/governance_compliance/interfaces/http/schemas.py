"""HTTP request/response schemas (contract frozen, issue #248)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GuardCheckBody(BaseModel):
    text: str = Field(min_length=1)
    speaker_kind: Literal["institution", "person", "anonymous"]
    invocation_id: str
    run_id: str | None = None
    position_id: str | None = None
    cited_passage_ids: list[str] = Field(default_factory=list)
    reference_figure_ids: list[str] = Field(default_factory=list)


class ViolationItem(BaseModel):
    violation_id: str
    violation_class: str
    offending_span: str
    rewritten_span: str | None
    rule_id: str
    rule_version: str
    detected_at: datetime


class GuardCheckResponse(BaseModel):
    decision: Literal["accept", "rewrite", "reject"]
    violations: list[ViolationItem]
    rewritten_text: str | None = None
    rule_version: str


class ViolationListResponse(BaseModel):
    items: list[ViolationItem]


class DiscloseProvenanceBody(BaseModel):
    version: int | None = Field(default=None, ge=1)
    requested_by: str | None = None


class ProvenanceResponse(BaseModel):
    position_id: str
    evidence_ids: list[str]
    argument_ids: list[str]
    invocation_id: str
    prompt_version: str
    model: str
    disclosed_at: datetime
    version: int


class AllowlistItem(BaseModel):
    code: str
    canonical_name: str
    short_name: str
    category: str
    aliases: list[str]


class AllowlistResponse(BaseModel):
    institutions: list[AllowlistItem]
    version: str


class AllowlistValidationResponse(BaseModel):
    valid: bool
    institution_count: int
    problems: list[str]
