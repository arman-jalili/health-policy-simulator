"""``ConsensusRecord`` aggregate root (implemented by issue #306).

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
from consensus_analysis.domain.errors import StanceNotInHistory
from consensus_analysis.domain.events import (
    ConsensusBlockedByVeto,
    ConsensusDetermined,
    DomainEvent,
    MinorityPositionRecorded,
    UnresolvedConflictDeclared,
)
from consensus_analysis.domain.services import ConsensusRule, MinorityCapture, ordered
from consensus_analysis.domain.values import (
    ConsensusId,
    ConsensusOutcome,
    ConsensusOutcomeKind,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    StakeholderId,
    StanceSnapshot,
    TopicRef,
    UnresolvedConflict,
)

_RULE = ConsensusRule()
"""One stateless rule instance: evaluation depends only on the arguments (no hidden state)."""


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
        return cls(
            id=consensus_id,
            run_id=run_id,
            topic=topic,
            proposal_class=proposal_class,
            threshold=threshold,
            stances=dict(stances),
            vetoes=dict(vetoes),
            log_position=log_position,
        )

    def determine(self) -> ConsensusOutcome:
        """Derive the outcome: veto first, then threshold, then minority (AC 1, AC 2)."""
        self.assert_stances_recorded()
        outcome = _RULE.evaluate(
            proposal_class=self.proposal_class,
            stances=self.stances,
            threshold=self.threshold,
            vetoes=self.vetoes,
        )
        self.outcome = outcome
        if outcome.kind is ConsensusOutcomeKind.VETO_BLOCKED:
            if outcome.veto is not None:
                self.events.append(
                    ConsensusBlockedByVeto(
                        run_id=self.run_id,
                        topic=self.topic,
                        proposal_class=self.proposal_class,
                        holder_ids=outcome.veto.holders,
                    )
                )
            return outcome

        self.events.append(
            ConsensusDetermined(
                run_id=self.run_id,
                topic=self.topic,
                support=outcome.support.value,
                threshold=self.threshold.required_share,
                supporters=self.supporting_stakeholders(),
            )
        )
        for position in MinorityCapture().capture(stances=self.stances):
            self.record_minority(position)

        if outcome.kind is ConsensusOutcomeKind.UNRESOLVED:
            apart = self._positions_apart()
            if len(apart) >= 2:
                self.declare_unresolved(UnresolvedConflict(topic=self.topic, positions=apart))
        return outcome

    def assert_stances_recorded(self) -> None:
        """Refuse any stance whose log provenance is missing (AC 3).

        Two ways to lack provenance are refused, and both are named in the error so the caller can
        repair the input: a stance flagged as not recorded, and a stance that cites no log position.
        The second is already impossible at construction time; checking it again here means the
        aggregate does not depend on every producer having been careful.
        """
        missing = tuple(
            str(snapshot.stakeholder)
            for snapshot in ordered(self.stances)
            if not snapshot.recorded or snapshot.log_position is None
        )
        if missing:
            raise StanceNotInHistory(missing)

    def record_minority(self, position: MinorityPosition) -> None:
        """Attach a recorded dissent so no disapproving holder is dropped (AC 8)."""
        if not position.holders:
            raise ValueError("a minority position must name at least one holder")
        self.minorities = (*self.minorities, position)
        self.events.append(
            MinorityPositionRecorded(
                run_id=self.run_id,
                topic=self.topic,
                holders=position.holders,
                objection_count=len(position.objections),
            )
        )

    def declare_unresolved(self, conflict: UnresolvedConflict) -> None:
        """Keep a conflict that is still open at run close (AC 2)."""
        self.unresolved = (*self.unresolved, conflict)
        self.events.append(
            UnresolvedConflictDeclared(
                run_id=self.run_id,
                topic=self.topic,
                positions=conflict.positions,
            )
        )

    def drain_events(self) -> tuple[DomainEvent, ...]:
        """Return and clear the pending events for the outbox in the saving transaction."""
        drained = tuple(self.events)
        self.events.clear()
        return drained

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
        return ordered(self.stances)

    def _positions_apart(self) -> tuple[StanceSnapshot, ...]:
        """Return the recorded positions that remain apart; abstentions express no conflict."""
        return tuple(
            snapshot
            for snapshot in self.ordered_stances()
            if snapshot.recorded and (snapshot.supports or snapshot.disapproves)
        )
