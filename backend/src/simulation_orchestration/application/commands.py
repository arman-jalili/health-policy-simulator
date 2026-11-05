"""Use-case request DTOs (contract frozen, issue #205)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from simulation_orchestration.application.values import (
    GraphState,
    InvocationId,
    InvocationOutcome,
    JobId,
    PauseAction,
    PromptRef,
    RunBudget,
    RunId,
)


@dataclass(frozen=True, slots=True)
class StartSimulationRequest:
    run_id: RunId
    budget: RunBudget = field(default_factory=RunBudget)
    requested_by: str | None = None


@dataclass(frozen=True, slots=True)
class StreamSimulationProgressRequest:
    run_id: RunId
    last_event_id: str | None = None
    limit: int = 100


@dataclass(frozen=True, slots=True)
class PauseOrResumeSimulationRequest:
    run_id: RunId
    action: PauseAction
    reason: str = "client_request"
    budget: RunBudget | None = None


@dataclass(frozen=True, slots=True)
class RecordAgentInvocationRequest:
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
    outcome: InvocationOutcome = InvocationOutcome.SUCCESS


@dataclass(frozen=True, slots=True)
class GetJobRequest:
    job_id: JobId


@dataclass(frozen=True, slots=True)
class CollectUsageReportRequest:
    run_id: RunId


@dataclass(frozen=True, slots=True)
class RegisterPromptTemplateRequest:
    name: str
    body: str


@dataclass(frozen=True, slots=True)
class ResolvePromptTemplateRequest:
    name: str
    version: int | None = None


@dataclass(frozen=True, slots=True)
class ApplyCheckpointRequest:
    job_id: JobId
    state: GraphState
