"""``CompromisePackage`` aggregate root (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Aggregate State, invariant 5)

A package combines only individually accepted, mutually compatible components, and it documents
every proposal that did not carry. Both obligations live here so a bundle can never be composed
silently around a rejected or incompatible part (invariant 5, AC 9).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from consensus_analysis.domain.entities import PackageComponent, RejectedProposal
from consensus_analysis.domain.events import DomainEvent
from consensus_analysis.domain.values import (
    ComponentId,
    LogPosition,
    PackageId,
    PackageState,
    RunId,
)


@dataclass
class CompromisePackage:
    """Bundle of individually accepted measures with its documented rejections."""

    id: PackageId
    run_id: RunId
    log_position: LogPosition
    components: tuple[PackageComponent, ...] = ()
    rejected_proposals: tuple[RejectedProposal, ...] = ()
    state: PackageState = PackageState.DRAFT
    events: list[DomainEvent] = field(default_factory=list)

    @classmethod
    def open(
        cls, *, package_id: PackageId, run_id: RunId, log_position: LogPosition
    ) -> CompromisePackage:
        """Open an empty draft package for one run."""
        raise NotImplementedError("CompromisePackage.open is implemented by issue #317")

    def add_component(self, component: PackageComponent) -> None:
        """Add one accepted component; compatibility is checked before the call (invariant 5)."""
        raise NotImplementedError("CompromisePackage.add_component is implemented by issue #317")

    def compose(self, *, rejected: Sequence[RejectedProposal]) -> None:
        """Close the draft and document every proposal that did not carry (AC 9)."""
        raise NotImplementedError("CompromisePackage.compose is implemented by issue #317")

    def abandon(self, *, reason: str) -> None:
        """Abandon a draft that produced no accepted component."""
        raise NotImplementedError("CompromisePackage.abandon is implemented by issue #317")

    def component_ids(self) -> tuple[ComponentId, ...]:
        """Return the accepted component ids in composition order, for the audit row."""
        return tuple(component.id for component in self.components)

    def drain_events(self) -> tuple[DomainEvent, ...]:
        """Return and clear the pending events for the outbox in the saving transaction."""
        raise NotImplementedError("CompromisePackage.drain_events is implemented by issue #317")
