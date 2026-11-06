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
from consensus_analysis.domain.errors import (
    IncompatibleComponent,
    IncompleteRejectionList,
    PackageStateTransition,
)
from consensus_analysis.domain.events import CompromisePackageComposed, DomainEvent
from consensus_analysis.domain.services import ComponentsCompatible
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
        """Add one accepted component, refusing one that conflicts with what is already inside.

        The check lives here rather than only in the use case: a package must not be composable
        around an incompatible part, whoever assembles it (invariant 5).
        """
        if self.state is not PackageState.DRAFT:
            raise PackageStateTransition(self.id, self.state.value, "add a component")
        for existing in self.components:
            if not ComponentsCompatible().is_satisfied_by(left=existing, right=component):
                raise IncompatibleComponent(
                    f"component {component.id} conflicts with {existing.id}",
                    details=[
                        {
                            "message": "declared incompatibility",
                            "field": str(component.id),
                            "code": "INCOMPATIBLE_COMPONENT",
                        }
                    ],
                )
        self.components = (*self.components, component)

    def compose(self, *, rejected: Sequence[RejectedProposal]) -> None:
        """Close the draft and document every proposal that did not carry (AC 9).

        No accepted component means no package: the aggregate becomes ``ABANDONED`` instead of a
        published empty bundle. Rejections are stored as given and counted once, so a rejection
        cannot vanish between assembly and the audit row.
        """
        if self.state is not PackageState.DRAFT:
            raise PackageStateTransition(self.id, self.state.value, "compose")
        seen: set[str] = set()
        for proposal in rejected:
            if not proposal.reason.strip():
                raise IncompleteRejectionList(proposal.measure)
            if str(proposal.id) in seen:
                raise IncompleteRejectionList(proposal.measure)
            seen.add(str(proposal.id))
        self.rejected_proposals = tuple(rejected)
        self.state = PackageState.COMPOSED if self.components else PackageState.ABANDONED
        self.events.append(
            CompromisePackageComposed(
                package_id=self.id,
                component_ids=self.component_ids(),
                rejected_count=len(self.rejected_proposals),
            )
        )

    def abandon(self, *, reason: str) -> None:
        """Abandon a draft that produced no accepted component."""
        self.state = PackageState.ABANDONED

    def component_ids(self) -> tuple[ComponentId, ...]:
        """Return the accepted component ids in composition order, for the audit row."""
        return tuple(component.id for component in self.components)

    def drain_events(self) -> tuple[DomainEvent, ...]:
        """Return and clear the pending events for the outbox in the saving transaction."""
        drained = tuple(self.events)
        self.events.clear()
        return drained
