"""HTTP request/response schemas (contract frozen, issue #205)."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class BudgetBody(BaseModel):
    max_invocations: int | None = Field(default=None, ge=0)
    max_tokens: int | None = Field(default=None, ge=0)
    max_cost: Decimal | None = Field(default=None, ge=0)


class StartBody(BaseModel):
    budget: BudgetBody = Field(default_factory=BudgetBody)


class StartResponse(BaseModel):
    job_id: str
    run_id: str
    status: str


class PauseResumeBody(BaseModel):
    action: Literal["pause", "resume"]
    reason: str = "client_request"
    budget: BudgetBody | None = None


class PauseResumeResponse(BaseModel):
    run_id: str
    status: str
    checkpoint_round: int | None = None
    checkpoint_phase: str | None = None


class GraphStateBody(BaseModel):
    run_id: str
    round: int
    phase: str
    next_actor: str | None
    budget_used_invocations: int
    budget_used_tokens: int
    budget_used_cost: Decimal


class JobResponse(BaseModel):
    job_id: str
    run_id: str
    status: str
    attempts: int
    checkpoint: GraphStateBody
    error: str | None
    progress_sequence: int


class StakeholderUsageItem(BaseModel):
    stakeholder: str
    invocations: int
    input_tokens: int
    output_tokens: int
    cost: Decimal


class RoundUsageItem(BaseModel):
    round: int
    invocations: int
    input_tokens: int
    output_tokens: int
    cost: Decimal


class UsageResponse(BaseModel):
    run_id: str
    total_invocations: int
    input_tokens: int
    output_tokens: int
    cost: Decimal
    by_stakeholder: list[StakeholderUsageItem]
    by_round: list[RoundUsageItem]


class ProgressEventBody(BaseModel):
    event_id: str
    sequence: int
    kind: str
    payload: dict[str, object]
