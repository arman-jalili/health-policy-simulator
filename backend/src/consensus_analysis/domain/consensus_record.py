"""``ConsensusRecord`` aggregate root (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Aggregate State, Invariants)

One record per (run, topic). It is derived: every input it cites must be present in the closed run
log, and ``determine`` never assumes agreement the record does not support. Veto precedence is part
of the aggregate's contract, not an ordering accident: a blocked class yields
``ConsensusOutcomeKind.VETO_BLOCKED`` at any support level (invariant 11, AC 1).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from consensus_analysis.domain.entities import MajorityPosition, MinorityPosition
from consensus_analysis.domain.events import DomainEvent
from consensus_analysis.domain.values import (
    ConsensusId,
    ConsensusOutcome,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    StakeholderId,
    StanceSnapshot,
    TopicRef,
    UnresolvedConflict,
)


@dataclass
class ConsensusRecord:
    """Derived per-topic outcome with its provenance and its audit events."""

    id: ConsensusId
    run_id: RunId
    topic: TopicRef
    proposal_class: ProposalClass
    threshold: ConsensusThreshold
    stances: Mapping[StakeholderId, StanceSnapshot]
    vetoes: Mapping[StakeholderId, frozenset[ProposalClass]]
    log_position: LogPosition
    outcome: ConsensusOutcome | None = None
    majority: MajorityPosition | None = None
    minorities: tuple[MinorityPosition, ...] = ()
    unresolved: tuple[UnresolvedConflict, ...] = ()
    events: list[DomainEvent] = field(default_factory=list)

    @classmethod
    def open(
        cls,
        *,
        consensus_id: ConsensusId,
        run_id: RunId,
        topic: TopicRef,
        proposal_class: ProposalClass,
        threshold: ConsensusThreshold,
        stances: Mapping[StakeholderId, StanceSnapshot],
        vetoes: Mapping[StakeholderId, frozenset[ProposalClass]],
        log_position: LogPosition,
    ) -> ConsensusRecord:
        """Open the record for one topic; nothing is concluded before ``determine`` (AC 3)."""
        raise NotImplementedError("ConsensusRecord.open is implemented by issue #306")

    def determine(self) -> ConsensusOutcome:
        """Derive the outcome: veto first, then threshold, then minority (AC 1, AC 2)."""
        raise NotImplementedError("ConsensusRecord.determine is implemented by issue #306")

    def assert_stances_recorded(self) -> None:
        """Refuse any stance whose log provenance is missing (AC 3)."""
        raise NotImplementedError(
            "ConsensusRecord.assert_stances_recorded is implemented by issue #311"
        )

    def record_minority(self, position: MinorityPosition) -> None:
        """Attach a recorded dissent so no disapproving holder is dropped (AC 8)."""
        raise NotImplementedError("ConsensusRecord.record_minority is implemented by issue #316")

    def declare_unresolved(self, conflict: UnresolvedConflict) -> None:
        """Keep a conflict that is still open at run close (AC 2)."""
        raise NotImplementedError("ConsensusRecord.declare_unresolved is implemented by issue #306")

    def drain_events(self) -> tuple[DomainEvent, ...]:
        """Return and clear the pending events for the outbox in the saving transaction."""
        raise NotImplementedError("ConsensusRecord.drain_events is implemented by issue #306")

    def digest(self) -> str:
        """Stable hash of the derived content; equal digests prove a rebuild (AC 4)."""
        raise NotImplementedError("ConsensusRecord.digest is implemented by issue #312")

    def minority_holders(self) -> tuple[StakeholderId, ...]:
        """Flatten every recorded minority into the holders the audit row must name."""
        return tuple(holder for position in self.minorities for holder in position.holders)

    def supporting_stakeholders(self) -> tuple[StakeholderId, ...]:
        """Return the recorded holders that approve the proposal, in log order."""
        return tuple(
            snapshot.stakeholder
            for snapshot in self.ordered_stances()
            if snapshot.recorded and snapshot.supports
        )

    def ordered_stances(self) -> Sequence[StanceSnapshot]:
        """Return the stances ordered by log position, so derivation is order-independent (W9)."""
        return tuple(
            sorted(
                self.stances.values(),
                key=lambda snapshot: (
                    snapshot.log_position if snapshot.log_position is not None else -1,
                    str(snapshot.stakeholder),
                ),
            )
        )
