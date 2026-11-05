"""Frozen progress-event payloads (issue #205).

ADR-008 forbids a ``domain/`` layer for service-depth contexts, so event schemas live in the
application layer. They carry no negotiation state: only ids, sequencing and budget facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from simulation_orchestration.application.values import (
    BudgetDimension,
    GraphState,
    InvocationId,
    JobId,
    PromptRef,
    RunId,
)


@dataclass(frozen=True, slots=True)
class RunQueued:
    name: ClassVar[str] = "RunQueued"
    job_id: JobId
    run_id: RunId


@dataclass(frozen=True, slots=True)
class RunStarted:
    name: ClassVar[str] = "RunStarted"
    job_id: JobId
    run_id: RunId


@dataclass(frozen=True, slots=True)
class RoundStarted:
    name: ClassVar[str] = "RoundStarted"
    run_id: RunId
    round: int


@dataclass(frozen=True, slots=True)
class TurnStarted:
    name: ClassVar[str] = "TurnStarted"
    run_id: RunId
    round: int
    stakeholder_id: str
    invocation_id: InvocationId


@dataclass(frozen=True, slots=True)
class TurnCompleted:
    name: ClassVar[str] = "TurnCompleted"
    run_id: RunId
    round: int
    stakeholder_id: str
    position_id: str | None


@dataclass(frozen=True, slots=True)
class RunPaused:
    name: ClassVar[str] = "RunPaused"
    run_id: RunId
    reason: str
    checkpoint: GraphState


@dataclass(frozen=True, slots=True)
class RunResumed:
    name: ClassVar[str] = "RunResumed"
    run_id: RunId
    checkpoint: GraphState


@dataclass(frozen=True, slots=True)
class RunCompleted:
    name: ClassVar[str] = "RunCompleted"
    run_id: RunId
    rounds: int


@dataclass(frozen=True, slots=True)
class RunFailed:
    name: ClassVar[str] = "RunFailed"
    run_id: RunId
    error: str
    attempts: int


@dataclass(frozen=True, slots=True)
class RunBudgetExhausted:
    name: ClassVar[str] = "RunBudgetExhausted"
    run_id: RunId
    dimension: BudgetDimension
    limit: Decimal
    used: Decimal


@dataclass(frozen=True, slots=True)
class AgentInvocationRecorded:
    name: ClassVar[str] = "AgentInvocationRecorded"
    run_id: RunId
    invocation_id: InvocationId
    prompt: PromptRef
    cost_estimate: Decimal


SimulationEvent = (
    RunQueued
    | RunStarted
    | RoundStarted
    | TurnStarted
    | TurnCompleted
    | RunPaused
    | RunResumed
    | RunCompleted
    | RunFailed
    | RunBudgetExhausted
    | AgentInvocationRecorded
)
