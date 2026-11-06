"""Projection rebuild: fold the run log into consensus rows (issue #312).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Wiring Contract, roadmap W9)

The rebuild is the proof that these tables are projections and not a second source of truth. It
reads only the log and the mandate facts, allocates rows by the log position they were derived from,
and produces the same content twice — which is what makes the equality assertion meaningful.

Rows are emitted in a stable topic order and keyed by the earliest log position of the topic, so a
rebuild is order-independent (W9) and never depends on dict insertion order.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from consensus_analysis.application.ports import IdFactory
from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.values import (
    AgendaItem,
    ConsensusId,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    StakeholderId,
    StanceSnapshot,
    TopicRef,
)


class LogFoldingRebuilder:
    """Event folding over the closed run log: the only producer of projection rows."""

    def __init__(self, *, ids: IdFactory) -> None:
        self._ids = ids

    def collaborators(self) -> tuple[object, ...]:
        """Ports this strategy requires (W8 reachability anchor)."""
        return (self._ids,)

    async def rebuild(
        self,
        *,
        run_id: RunId,
        agenda: Sequence[AgendaItem],
        stances: Sequence[StanceSnapshot],
        vetoes: dict[StakeholderId, frozenset[ProposalClass]],
        threshold: ConsensusThreshold,
    ) -> Sequence[ConsensusRecord]:
        """Fold the log into one record per agenda item, in a stable order."""
        by_topic = _group_by_topic(stances)
        records: list[ConsensusRecord] = []
        for item in sorted(agenda, key=lambda entry: str(entry.topic)):
            positions = by_topic.get(item.topic, ())
            record = ConsensusRecord.open(
                consensus_id=ConsensusId(self._ids.new_id("cns")),
                run_id=run_id,
                topic=item.topic,
                proposal_class=item.proposal_class,
                threshold=threshold,
                stances={snapshot.stakeholder: snapshot for snapshot in positions},
                vetoes=vetoes,
                log_position=_earliest_position(positions),
            )
            record.determine()
            records.append(record)
        return tuple(records)


def _group_by_topic(
    stances: Iterable[StanceSnapshot],
) -> dict[TopicRef, list[StanceSnapshot]]:
    grouped: dict[TopicRef, list[StanceSnapshot]] = {}
    for snapshot in stances:
        grouped.setdefault(snapshot.topic, []).append(snapshot)
    return grouped


def _earliest_position(positions: Sequence[StanceSnapshot]) -> LogPosition:
    """Key the row by the log position it derives from, never by insertion order (W9)."""
    known = [snapshot.log_position for snapshot in positions if snapshot.log_position is not None]
    if not known:
        return LogPosition(0)
    return LogPosition(min(int(position) for position in known))
