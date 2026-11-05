"""Domain rules as plain application collaborators (contract frozen, issue #205).

ADR-008 service depth: these are stateless policy objects, not aggregates. Bodies are TODO until
their implementation issues land; the signatures and return types are frozen now.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from simulation_orchestration.application.values import (
    BudgetDecision,
    BudgetUsage,
    GraphState,
    PauseAction,
    PauseDecision,
    PromptTemplate,
    RunBudget,
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
        raise NotImplementedError("BudgetGuard is implemented by issue #209")


class CheckpointPolicy:
    """Decide which states are safe to persist for resume/crash recovery."""

    def is_safe_boundary(self, state: GraphState) -> bool:
        raise NotImplementedError("CheckpointPolicy is implemented by issue #212")

    def checkpoint(self, state: GraphState) -> GraphState:
        raise NotImplementedError("CheckpointPolicy is implemented by issue #212")


class PauseBoundary:
    """Pause is honoured only between turns; the current turn completes or discards atomically."""

    def can_pause(self, state: GraphState) -> bool:
        raise NotImplementedError("PauseBoundary is implemented by issue #210")

    def resolve(
        self, *, action: PauseAction, state: GraphState, turn_committed: bool
    ) -> PauseDecision:
        raise NotImplementedError("PauseBoundary is implemented by issue #210")


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
