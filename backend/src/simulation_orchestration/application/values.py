"""Frozen value vocabulary of SimulationOrchestration (issue #205).

Service depth (ADR-008): these are contract values, not domain aggregates or value objects.
Canonical: .pi/architecture/modules/simulation-orchestration.md
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, NewType

JobId = NewType("JobId", str)
RunId = NewType("RunId", str)
InvocationId = NewType("InvocationId", str)
EventId = NewType("EventId", str)
PromptId = NewType("PromptId", str)


class JobStatus(StrEnum):
    """Persisted job lifecycle. Terminal states are COMPLETED and FAILED."""

    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    BUDGET_EXHAUSTED = "budget_exhausted"


class RunPhase(StrEnum):
    """Negotiation phase as reported by the ACL. The graph never owns domain state."""

    MANDATE = "mandate"
    SELECT = "select"
    OPEN = "open"
    ROUNDS = "rounds"
    CLOSE = "close"
    DONE = "done"


class PauseAction(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"


class InvocationOutcome(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    BUDGET_REJECTED = "budget_rejected"


class BudgetDimension(StrEnum):
    INVOCATIONS = "invocations"
    TOKENS = "tokens"
    COST = "cost"


class ProgressKind(StrEnum):
    """Stable SSE ``event:`` names. Ordering is carried by ``sequence``, not by this enum."""

    QUEUED = "run.queued"
    STARTED = "run.started"
    ROUND_STARTED = "round.started"
    TURN_STARTED = "turn.started"
    TURN_COMPLETED = "turn.completed"
    PAUSED = "run.paused"
    RESUMED = "run.resumed"
    COMPLETED = "run.completed"
    FAILED = "run.failed"
    BUDGET_EXHAUSTED = "run.budget_exhausted"
    INVOCATION_RECORDED = "invocation.recorded"


@dataclass(frozen=True, slots=True)
class RunBudget:
    """Optional caps. ``None`` means that dimension is unbounded."""

    max_invocations: int | None = None
    max_tokens: int | None = None
    max_cost: Decimal | None = None


@dataclass(frozen=True, slots=True)
class BudgetUsage:
    invocations: int = 0
    tokens: int = 0
    cost: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    allowed: bool
    dimension: BudgetDimension | None = None
    limit: Decimal | None = None
    used: Decimal | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class GraphState:
    """The only state the graph may hold (ADR-003).

    No positions, arguments, evidence, prompts or persona data belong here.
    """

    run_id: RunId
    round: int
    phase: RunPhase
    next_actor: str | None
    budget_used: BudgetUsage


@dataclass(frozen=True, slots=True)
class PromptRef:
    """``name@version`` identity persisted with every invocation."""

    name: str
    version: int

    @property
    def identity(self) -> str:
        return f"{self.name}@{self.version}"


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    id: PromptId
    name: str
    version: int
    body: str
    checksum: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """USD per 1K tokens. A missing entry must fail at boot, never meter zero."""

    model_id: str
    input_per_1k: Decimal
    output_per_1k: Decimal


@dataclass(frozen=True, slots=True)
class LLMRequest:
    model: str
    prompt: str
    prompt_ref: PromptRef
    parameters: Mapping[str, Any]
    evidence_pack_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


@dataclass(frozen=True, slots=True)
class NegotiationRunView:
    """ACL projection of NegotiationSession. Contains sequencing facts only."""

    run_id: RunId
    phase: RunPhase
    round: int
    next_actor: str | None
    terminal: bool


@dataclass(frozen=True, slots=True)
class NegotiationTurnCommand:
    run_id: RunId
    round: int
    actor_id: str
    invocation_id: InvocationId


@dataclass(frozen=True, slots=True)
class NegotiationTurnView:
    run_id: RunId
    round: int
    actor_id: str
    position_id: str | None
    terminal: bool


@dataclass(frozen=True, slots=True)
class PauseDecision:
    """Outcome of evaluating a pause at a turn boundary."""

    accepted: bool
    checkpoint: GraphState | None
    reason: str | None = None
