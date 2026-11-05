"""In-memory adapters used by component tests and local wiring (issues #208+)."""

from __future__ import annotations

from decimal import Decimal

from simulation_orchestration.application.dto import (
    InvocationEnvelope,
    RoundUsage,
    StakeholderUsage,
    UsageAggregate,
)
from simulation_orchestration.application.values import RunId


class InMemoryInvocationStore:
    """Append-only envelope store, unique on invocation id, with real usage aggregation."""

    def __init__(self) -> None:
        self._envelopes: dict[str, InvocationEnvelope] = {}

    async def add(self, envelope: InvocationEnvelope) -> None:
        self._envelopes.setdefault(str(envelope.invocation_id), envelope)

    async def list_for_run(self, run_id: RunId) -> list[InvocationEnvelope]:
        return [item for item in self._envelopes.values() if item.run_id == run_id]

    async def usage_for_run(self, run_id: RunId) -> UsageAggregate:
        envelopes = await self.list_for_run(run_id)
        by_stakeholder: dict[str, list[InvocationEnvelope]] = {}
        by_round: dict[int, list[InvocationEnvelope]] = {}
        for envelope in envelopes:
            by_stakeholder.setdefault(envelope.stakeholder, []).append(envelope)
            by_round.setdefault(envelope.round, []).append(envelope)
        return UsageAggregate(
            invocations=len(envelopes),
            input_tokens=sum(item.input_tokens for item in envelopes),
            output_tokens=sum(item.output_tokens for item in envelopes),
            cost=sum((item.cost_estimate for item in envelopes), Decimal("0")),
            by_stakeholder=tuple(
                _stakeholder_usage(name, items) for name, items in sorted(by_stakeholder.items())
            ),
            by_round=tuple(
                _round_usage(round_no, items) for round_no, items in sorted(by_round.items())
            ),
        )


def _stakeholder_usage(name: str, items: list[InvocationEnvelope]) -> StakeholderUsage:
    return StakeholderUsage(
        stakeholder=name,
        invocations=len(items),
        input_tokens=sum(item.input_tokens for item in items),
        output_tokens=sum(item.output_tokens for item in items),
        cost=sum((item.cost_estimate for item in items), Decimal("0")),
    )


def _round_usage(round_no: int, items: list[InvocationEnvelope]) -> RoundUsage:
    return RoundUsage(
        round=round_no,
        invocations=len(items),
        input_tokens=sum(item.input_tokens for item in items),
        output_tokens=sum(item.output_tokens for item in items),
        cost=sum((item.cost_estimate for item in items), Decimal("0")),
    )
