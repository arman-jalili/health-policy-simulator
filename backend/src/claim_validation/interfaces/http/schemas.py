"""HTTP request/response bodies (contract frozen, issue #164)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MeasureBody(BaseModel):
    measure: str
    unit: str
    period: str
    geography: str


class VerifyClaimBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    claim_type: str | None = None
    measure: MeasureBody | None = None
    asserted_value: str | None = None


class ClaimVerdictResponse(BaseModel):
    claim_id: str
    verdict: str
    path: str
    claim_type: str
    sources: list[str]
    delta: str | None = None


class ClaimDetailResponse(ClaimVerdictResponse):
    text: str
    review_verdict: str | None = None
    review_basis: str | None = None


class FlagBody(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ReferenceFigureBody(BaseModel):
    measure: MeasureBody
    value: str
    tier: str
    as_of: str
    source_id: str


class ReferenceFigureResponse(BaseModel):
    figure_id: str


class ReferenceFigureItem(BaseModel):
    figure_id: str
    measure: str
    unit: str
    period: str
    geography: str
    value: str
    tier: str
    as_of: str
    source_id: str


class ReferenceFiguresResponse(BaseModel):
    items: list[ReferenceFigureItem]


class ContradictionItem(BaseModel):
    finding_id: str
    claim_id_a: str
    claim_id_b: str
    measure: str
    delta: str


class ContradictionResponse(BaseModel):
    items: list[ContradictionItem]


class ReviewBody(BaseModel):
    verdict: str
    basis: str
