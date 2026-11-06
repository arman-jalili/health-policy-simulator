"""``DecisionBrief`` aggregate root — frozen contract (issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Aggregate root, Invariants)

A generated projection that is frozen at publication: it has identity, immutable published versions
and citation integrity enforced at publication. The query helpers below are part of the frozen
surface because every gate reads them; the gating methods themselves belong to the implementation
issues named in their ``NotImplementedError``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.events import DomainEvent
from decision_brief.domain.values import (
    REQUIRED_SECTIONS,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitationReference,
    CitedStatement,
    RunId,
    SectionKind,
    SimulationDisclaimer,
    TopicOutcome,
)


@dataclass
class DecisionBrief:
    """Versioned jury-facing artefact; ``PUBLISHED`` versions are immutable."""

    id: BriefId
    run_id: RunId
    version: BriefVersion
    sections: dict[SectionKind, BriefSection]
    rejected_proposals: tuple[RejectedProposalRecord, ...] = ()
    disclaimer: SimulationDisclaimer | None = None
    outcomes: tuple[TopicOutcome, ...] = ()
    status: BriefStatus = BriefStatus.DRAFT
    events: list[DomainEvent] = field(default_factory=list)

    def missing_sections(self) -> frozenset[SectionKind]:
        """Mandated kinds absent from this brief (AC 1)."""
        return REQUIRED_SECTIONS - set(self.sections)

    def unresolved_citations(self) -> tuple[CitationReference, ...]:
        """Every citation with no resolved provenance, in reading order (AC 2)."""
        return tuple(
            citation
            for section in self.sections.values()
            for statement in section.statements
            for citation in statement.citations
            if not citation.is_resolved()
        )

    def is_published(self) -> bool:
        """Whether the artefact is frozen and read-only (AC 6)."""
        return self.status is BriefStatus.PUBLISHED

    def assert_statement_evidence(self, statement: CitedStatement) -> None:
        """Raise ``StatementWithoutCitation`` for an evidenced statement with no citation (AC 5)."""
        raise NotImplementedError(
            "DecisionBrief.assert_statement_evidence is implemented by "
            "issue-decision-brief-statement-evidence"
        )

    def publish(self) -> None:
        """Run every gate, then freeze: sections, citations, disclosures, disclaimer (AC 1-4)."""
        raise NotImplementedError(
            "DecisionBrief.publish is implemented by issue-decision-brief-eight-sections"
        )

    def assert_immutable(self) -> None:
        """Raise ``PublishedBriefIsImmutable`` when a published brief would change (AC 6)."""
        raise NotImplementedError(
            "DecisionBrief.assert_immutable is implemented by issue-decision-brief-immutability"
        )

    def supersede_by(self, successor: DecisionBrief, *, reason: str) -> DecisionBrief:
        """Return the successor version N+1 that references this version and the reason (AC 7)."""
        raise NotImplementedError(
            "DecisionBrief.supersede_by is implemented by issue-decision-brief-lineage"
        )
