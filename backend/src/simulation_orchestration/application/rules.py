"""Domain rules as plain application collaborators (contract frozen, issue #205).

ADR-008 service depth: these are stateless policy objects, not aggregates. Bodies are TODO until
their implementation issues land; the signatures and return types are frozen now.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from shared.ids import new_id
from shared.metrics import METRICS
from simulation_orchestration.application.events import RunBudgetExhausted
from simulation_orchestration.application.values import (
    BudgetDecision,
    BudgetDimension,
    BudgetUsage,
    GraphState,
    PauseAction,
    PauseDecision,
    PromptId,
    PromptTemplate,
    RunBudget,
    RunId,
    RunPhase,
)


class BudgetGuard:
    """Pre-call check over invocations, tokens and cost (ADR-006)."""

    def evaluate(
        self,
        *,
        budget: RunBudget,
        usage: BudgetUsage,
        requested_tokens: int,
        requested_cost: Decimal,
    ) -> BudgetDecision:
        if requested_tokens < 0 or requested_cost < 0:
            raise ValueError("requested tokens and cost must not be negative")
        checks = (
            (
                BudgetDimension.INVOCATIONS,
                budget.max_invocations,
                Decimal(usage.invocations + 1),
            ),
            (BudgetDimension.TOKENS, budget.max_tokens, Decimal(usage.tokens + requested_tokens)),
            (BudgetDimension.COST, budget.max_cost, usage.cost + requested_cost),
        )
        for dimension, limit, used in checks:
            if limit is not None and used > Decimal(limit):
                METRICS.increment(
                    "simulation_budget_exhausted_total", {"dimension": dimension.value}
                )
                return BudgetDecision(
                    allowed=False,
                    dimension=dimension,
                    limit=Decimal(limit),
                    used=used,
                    reason=f"{dimension.value} budget exhausted: {used} > {limit}",
                )
        return BudgetDecision(allowed=True)

    def exhaustion_event(self, run_id: RunId, decision: BudgetDecision) -> RunBudgetExhausted:
        """Build the event for a rejected call; the caller pauses the job atomically."""
        if decision.allowed or decision.dimension is None:
            raise ValueError("only a rejected budget decision can produce an exhaustion event")
        if decision.limit is None or decision.used is None:
            raise ValueError("a rejected budget decision must carry limit and used")
        return RunBudgetExhausted(
            run_id=run_id,
            dimension=decision.dimension,
            limit=decision.limit,
            used=decision.used,
        )


class CheckpointPolicy:
    """Decide which states are safe to persist for resume/crash recovery."""

    def is_safe_boundary(self, state: GraphState) -> bool:
        return state.phase is not RunPhase.DONE

    def checkpoint(self, state: GraphState) -> GraphState:
        if not self.is_safe_boundary(state):
            raise ValueError("cannot checkpoint a terminal graph state")
        return state


class PauseBoundary:
    """Pause is honoured only between turns; the current turn completes or discards atomically."""

    def can_pause(self, state: GraphState) -> bool:
        return state.phase is not RunPhase.DONE

    def resolve(
        self, *, action: PauseAction, state: GraphState, turn_committed: bool
    ) -> PauseDecision:
        if action is PauseAction.RESUME:
            return PauseDecision(accepted=True, checkpoint=state)
        if not self.can_pause(state):
            return PauseDecision(
                accepted=False,
                checkpoint=None,
                reason="run is already terminal",
            )
        if not turn_committed:
            return PauseDecision(
                accepted=True,
                checkpoint=state,
                reason="in-flight turn discarded before checkpoint",
            )
        return PauseDecision(accepted=True, checkpoint=state)


class RetryPolicy:
    """Bounded exponential backoff and dead-letter decision."""

    def __init__(
        self, *, max_attempts: int = 3, base_delay_s: float = 1.0, max_delay_s: float = 30.0
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if base_delay_s <= 0 or max_delay_s <= 0:
            raise ValueError("retry delays must be positive")
        self._max_attempts = max_attempts
        self._base_delay_s = base_delay_s
        self._max_delay_s = max_delay_s

    def should_retry(self, *, attempts: int, error: str) -> bool:
        return attempts < self._max_attempts and bool(error.strip())

    def delay_seconds(self, attempts: int) -> float:
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        delay = self._base_delay_s * (2 ** (attempts - 1))
        return float(min(delay, self._max_delay_s))


class PromptVersioning:
    """Append-only prompt versions; body changes create a version, identical bodies do not."""

    def next_version(
        self, *, existing: Sequence[PromptTemplate], name: str, body: str
    ) -> PromptTemplate:
        if not name.strip():
            raise ValueError("prompt name must not be empty")
        if not body.strip():
            raise ValueError("prompt body must not be empty")
        checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if existing:
            latest = max(existing, key=lambda item: item.version)
            if latest.body == body:
                return latest
            version = latest.version + 1
        else:
            version = 1
        return PromptTemplate(
            id=PromptId(new_id("prm")),
            name=name,
            version=version,
            body=body,
            checksum=checksum,
            created_at=datetime.now(tz=UTC),
        )
