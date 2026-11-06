"""Frozen domain services of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Service classification)

Classification is frozen here for every named service of the context, including the ports whose
adapters live in ``infrastructure/`` and the renderer that lives in ``interfaces/``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.projections import (
    ClaimVerdictProjection,
    CompromiseRecord,
    ConflictRecord,
    ConsensusProjection,
    HistoryEntry,
    RunProjection,
)
from decision_brief.domain.values import (
    SECTION_ORDINAL,
    ActorSummary,
    CitationReference,
    CitedStatement,
    EvidenceStatus,
    SectionKind,
    SimulationDisclaimer,
    TopicOutcome,
)

SERVICE_CLASSIFICATION: Mapping[str, str] = MappingProxyType(
    {
        "PublishDecisionBrief": "application",
        "VersionDecisionBrief": "application",
        "GetDecisionBrief": "application",
        "ListBriefVersions": "application",
        "ListCitations": "application",
        "BriefProjectionBuilder": "domain",
        "SectionAssembler": "domain",
        "ReproductionChecker": "domain",
        "OutcomeHonestyPolicy": "domain",
        "CitationResolver": "infrastructure",
        "ProvenanceDisclosureGate": "infrastructure",
        "BriefRenderer": "interfaces",
    }
)
"""Where every service of this context belongs (AC: service classification)."""


@runtime_checkable
class BriefProjectionBuilder(Protocol):
    """Pure assembly of the eight sections from local projections; no I/O in the mapping rules."""

    def build(
        self,
        *,
        run: RunProjection,
        consensus: ConsensusProjection,
        disclaimer: SimulationDisclaimer,
    ) -> DecisionBrief: ...


@runtime_checkable
class ReproductionChecker(Protocol):
    """Prove the artefact is a projection: regeneration reproduces it (invariant 7, AC 8)."""

    def assert_reproduces(self, published: DecisionBrief, regenerated: DecisionBrief) -> None: ...


@runtime_checkable
class OutcomeHonestyPolicy(Protocol):
    """A veto-blocked or ambiguous topic is stated as such, never smoothed into agreement (AC 9)."""

    def assert_honest(self, outcomes: Sequence[TopicOutcome]) -> None: ...


@dataclass(frozen=True, slots=True)
class SectionAssembler:
    """Pure mapping from the local projections to the eight mandated sections (issue #335).

    No I/O, no ambient state and no iteration over unordered collections: the same projections
    always produce the same sections, which is what makes the artefact reproducible (invariant 7).
    Statements that cite evidence stay ``EVIDENCED`` and carry unresolved citation references — the
    citation gate, not the assembler, decides whether they resolve.
    """

    def assemble(
        self, *, run: RunProjection, consensus: ConsensusProjection
    ) -> dict[SectionKind, BriefSection]:
        """Return all eight sections, each at its frozen ordinal."""
        return {
            SectionKind.QUESTION: self._section(
                SectionKind.QUESTION, (self._narrative(run.question),)
            ),
            SectionKind.ACTORS: self._section(
                SectionKind.ACTORS, tuple(self._actor(actor) for actor in run.actors)
            ),
            SectionKind.HISTORY: self._section(
                SectionKind.HISTORY, tuple(self._history(entry) for entry in run.history)
            ),
            SectionKind.CONFLICTS: self._section(
                SectionKind.CONFLICTS, tuple(self._conflict(item) for item in run.conflicts)
            ),
            SectionKind.COMPROMISES: self._section(
                SectionKind.COMPROMISES,
                (
                    *(self._compromise(item) for item in run.compromises),
                    *(self._rejection(item) for item in run.rejected_proposals),
                ),
            ),
            SectionKind.CONSENSUS: self._section(
                SectionKind.CONSENSUS, self._consensus_statements(run, consensus)
            ),
            SectionKind.OPEN_DISPUTES: self._section(
                SectionKind.OPEN_DISPUTES,
                tuple(self._outcome_statement(item) for item in self.outcomes(run, consensus)),
            ),
            SectionKind.IMPACT: self._section(
                SectionKind.IMPACT,
                tuple(self._narrative(text) for text in consensus.impact),
            ),
        }

    def outcomes(
        self, run: RunProjection, consensus: ConsensusProjection
    ) -> tuple[TopicOutcome, ...]:
        """Every topic stated honestly: blocked topics first, then still-open disputes."""
        return (*run.blocked_topics, *consensus.unresolved)

    # ── statement builders ─────────────────────────────────────────────────────────

    def _section(self, kind: SectionKind, statements: tuple[CitedStatement, ...]) -> BriefSection:
        return BriefSection(kind=kind, ordinal=SECTION_ORDINAL[kind], statements=statements)

    def _narrative(self, text: str) -> CitedStatement:
        return CitedStatement(text=text, status=EvidenceStatus.NARRATIVE)

    def _actor(self, actor: ActorSummary) -> CitedStatement:
        parts = [actor.institution]
        if actor.goals:
            parts.append(f"goals: {'; '.join(actor.goals)}")
        if actor.constraints:
            parts.append(f"constraints: {'; '.join(actor.constraints)}")
        if actor.adopted_positions:
            parts.append(f"positions: {'; '.join(actor.adopted_positions)}")
        return self._narrative(
            f"{parts[0]} — {' | '.join(parts[1:])}" if len(parts) > 1 else parts[0]
        )

    def _history(self, entry: HistoryEntry) -> CitedStatement:
        stance = f" ({entry.stance})" if entry.stance else ""
        return self._narrative(f"Round {entry.round_no} — {entry.actor}{stance}: {entry.summary}")

    def _conflict(self, item: ConflictRecord) -> CitedStatement:
        holders = f" [{', '.join(item.holders)}]" if item.holders else ""
        return self._narrative(f"{item.topic}{holders}: {item.summary}")

    def _compromise(self, item: CompromiseRecord) -> CitedStatement:
        parts = [item.measure]
        if item.supporters:
            parts.append(f"supported by {', '.join(item.supporters)}")
        if item.opponents:
            parts.append(f"opposed by {', '.join(item.opponents)}")
        return self._narrative(" — ".join(parts))

    def rejected_proposals(self, run: RunProjection) -> tuple[RejectedProposalRecord, ...]:
        """The run's refusals, carried onto the brief so the disclosure gate can check them."""
        return run.rejected_proposals

    def _rejection(self, item: RejectedProposalRecord) -> CitedStatement:
        blockers = ", ".join(item.blocking_stakeholders)
        reasons = "; ".join(item.reasons)
        detail = f" — blocked by {blockers}" if blockers else ""
        if reasons:
            detail = f"{detail}: {reasons}" if detail else f" — {reasons}"
        return self._narrative(f"{item.measure} — rejected{detail}")

    def _consensus_statements(
        self, run: RunProjection, consensus: ConsensusProjection
    ) -> tuple[CitedStatement, ...]:
        agreed = tuple(
            self._narrative(
                f"{item.topic}: {item.statement}"
                + (f" (majority: {', '.join(item.supporters)})" if item.supporters else "")
                + (f" (minority: {', '.join(item.minorities)})" if item.minorities else "")
            )
            for item in consensus.statements
        )
        verdicts = tuple(self._verdict_statement(item) for item in run.claim_verdicts)
        return (*agreed, *verdicts)

    def _verdict_statement(self, item: ClaimVerdictProjection) -> CitedStatement:
        if not item.passage_ids:
            return CitedStatement(
                text=f"Claim {item.claim_id}: {item.verdict} (no citable passage)",
                status=EvidenceStatus.UNSUPPORTED,
                claim_ids=(item.claim_id,),
            )
        return CitedStatement(
            text=f"Claim {item.claim_id}: {item.verdict}",
            status=EvidenceStatus.EVIDENCED,
            citations=tuple(CitationReference(passage_id=p) for p in item.passage_ids),
            claim_ids=(item.claim_id,),
        )

    def _outcome_statement(self, item: TopicOutcome) -> CitedStatement:
        parts = [f"{item.topic}: {item.kind.value.replace('_', ' ')}"]
        if item.blocking_stakeholders:
            parts.append(f"blocked by {', '.join(item.blocking_stakeholders)}")
        if item.reason:
            parts.append(item.reason)
        return self._narrative(" — ".join(parts))
