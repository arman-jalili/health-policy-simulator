"""Use-case result DTOs and persistence-facing records (contract frozen, issue #205)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from simulation_orchestration.application.values import (
    BudgetUsage,
    GraphState,
    InvocationId,
    InvocationOutcome,
    JobId,
    JobStatus,
    ProgressKind,
    PromptRef,
    RunBudget,
    RunId,
)


@dataclass(frozen=True, slots=True)
class StartSimulationResult:
    job_id: JobId
    run_id: RunId
    status: JobStatus


@dataclass(frozen=True, slots=True)
class PauseResumeResult:
    run_id: RunId
    status: JobStatus
    checkpoint: GraphState | None = None


@dataclass(frozen=True, slots=True)
class JobSnapshotResult:
    job_id: JobId
    run_id: RunId
    status: JobStatus
    attempts: int
    checkpoint: GraphState
    budget_used: BudgetUsage
    error: str | None
    progress_sequence: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class InvocationEnvelope:
    """The reproducibility record written by every LLM call (ADR-006)."""

    invocation_id: InvocationId
    run_id: RunId
    round: int
    stakeholder: str
    purpose: str
    model: str
    prompt: PromptRef
    parameters: Mapping[str, Any]
    evidence_pack_ids: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    cost_estimate: Decimal
    latency_ms: int
    outcome: InvocationOutcome
    created_at: datetime


@dataclass(frozen=True, slots=True)
class InvocationRecordResult:
    invocation_id: InvocationId
    run_id: RunId
    prompt: PromptRef
    cost_estimate: Decimal


@dataclass(frozen=True, slots=True)
class ProgressEventView:
    event_id: str
    run_id: RunId
    sequence: int
    kind: ProgressKind
    payload: Mapping[str, Any]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StakeholderUsage:
    stakeholder: str
    invocations: int
    input_tokens: int
    output_tokens: int
    cost: Decimal


@dataclass(frozen=True, slots=True)
class RoundUsage:
    round: int
    invocations: int
    input_tokens: int
    output_tokens: int
    cost: Decimal


@dataclass(frozen=True, slots=True)
class UsageReportResult:
    run_id: RunId
    total_invocations: int
    input_tokens: int
    output_tokens: int
    cost: Decimal
    by_stakeholder: tuple[StakeholderUsage, ...]
    by_round: tuple[RoundUsage, ...]


@dataclass(frozen=True, slots=True)
class PromptTemplateResult:
    id: str
    name: str
    version: int
    body: str
    checksum: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: JobId
    run_id: RunId
    status: JobStatus
    attempts: int
    checkpoint: GraphState
    budget_used: BudgetUsage
    error: str | None
    claimed_by: str | None
    created_at: datetime
    updated_at: datetime
    budget: RunBudget = field(default_factory=RunBudget)


@dataclass(frozen=True, slots=True)
class UsageAggregate:
    invocations: int
    input_tokens: int
    output_tokens: int
    cost: Decimal
    by_stakeholder: tuple[StakeholderUsage, ...] = ()
    by_round: tuple[RoundUsage, ...] = ()
