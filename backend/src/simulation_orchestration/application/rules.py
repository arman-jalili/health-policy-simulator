"""Domain rules as plain application collaborators (contract frozen, issue #205).

ADR-008 service depth: these are stateless policy objects, not aggregates. Bodies are TODO until
their implementation issues land; the signatures and return types are frozen now.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from simulation_orchestration.application.events import RunBudgetExhausted
from simulation_orchestration.application.values import (
    BudgetDecision,
    BudgetDimension,
    BudgetUsage,
    GraphState,
    PauseAction,
    PauseDecision,
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
        raise NotImplementedError("CheckpointPolicy is implemented by issue #212")

    def checkpoint(self, state: GraphState) -> GraphState:
        raise NotImplementedError("CheckpointPolicy is implemented by issue #212")


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

    def should_retry(self, *, attempts: int, error: str) -> bool:
        raise NotImplementedError("RetryPolicy is implemented by issue #212")

    def delay_seconds(self, attempts: int) -> float:
        raise NotImplementedError("RetryPolicy is implemented by issue #212")


class PromptVersioning:
    """Append-only prompt versions; body changes create a version, identical bodies do not."""

    def next_version(
        self, *, existing: Sequence[PromptTemplate], name: str, body: str
    ) -> PromptTemplate:
        raise NotImplementedError("PromptVersioning is implemented by issue #214")
