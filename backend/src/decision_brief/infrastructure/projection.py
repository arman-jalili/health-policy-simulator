"""Projection-builder adapter of DecisionBrief (issue #346).

The pure mapping lives in ``domain/services.SectionAssembler``; this adapter adds the only things
that are not domain decisions — a fresh brief identity and a version marker from the clock — and
returns a draft the publication use case can gate.
"""

from __future__ import annotations

from decision_brief.application.ports import Clock, IdFactory
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.projections import ConsensusProjection, RunProjection
from decision_brief.domain.services import SectionAssembler
from decision_brief.domain.values import BriefId, BriefVersion, SimulationDisclaimer


class BriefProjectionAdapter:
    """Assemble the eight sections and wrap them in a draft brief."""

    def __init__(self, *, ids: IdFactory, clock: Clock) -> None:
        self._ids = ids
        self._clock = clock
        self._assembler = SectionAssembler()

    def build(
        self,
        *,
        run: RunProjection,
        consensus: ConsensusProjection,
        disclaimer: SimulationDisclaimer,
    ) -> DecisionBrief:
        return DecisionBrief(
            id=BriefId(self._ids.new_id("brf")),
            run_id=run.run_id,
            version=BriefVersion(
                number=1,
                run_id=run.run_id,
                snapshot_ref=run.snapshot_ref,
                generated_at=self._clock.now(),
            ),
            sections=self._assembler.assemble(run=run, consensus=consensus),
            rejected_proposals=self._assembler.rejected_proposals(run),
            outcomes=self._assembler.outcomes(run, consensus),
            disclaimer=disclaimer,
        )
