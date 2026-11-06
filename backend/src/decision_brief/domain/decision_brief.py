"""``DecisionBrief`` aggregate root (issue #332).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Aggregate root, Invariants)

A generated projection that is frozen at publication: it has identity, immutable published versions
and citation integrity enforced at publication. ``publish`` is the single entry point that runs the
gates in reading order — completeness, statement evidence, citation integrity, disclosure — and only
then freezes the artefact, so a blocked brief keeps its audit events and never half-publishes.

Rejected-proposal completeness cannot be judged by the aggregate alone (it needs the run), so the
use case calls :meth:`DecisionBrief.assert_rejected_proposals_disclosed` with the run's recorded
measures before it calls ``publish``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.errors import (
    DisclosureMissing,
    IncompleteBrief,
    PublishedBriefIsImmutable,
    StatementWithoutCitation,
    UnresolvedCitation,
)
from decision_brief.domain.events import (
    BriefBlockedByMissingDisclosure,
    CitationResolutionFailed,
    DecisionBriefPublished,
    DomainEvent,
)
from decision_brief.domain.values import (
    REQUIRED_SECTIONS,
    SECTION_ORDINAL,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitationReference,
    CitedStatement,
    EvidenceStatus,
    RunId,
    SectionKind,
    SimulationDisclaimer,
    TopicOutcome,
)
from shared.errors import AppError

DISCLAIMER_DISCLOSURE = "simulation_disclaimer"
REJECTED_PROPOSALS_DISCLOSURE = "rejected_proposals"


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

    def citation_count(self) -> int:
        """How many citations the artefact carries; part of the publication event payload."""
        return sum(
            len(statement.citations)
            for section in self.sections.values()
            for statement in section.statements
        )

    def is_published(self) -> bool:
        """Whether the artefact is frozen and read-only (AC 6)."""
        return self.status is BriefStatus.PUBLISHED

    def assert_statement_evidence(self, statement: CitedStatement) -> None:
        """Raise ``StatementWithoutCitation`` for an evidenced statement with no citation (AC 5)."""
        if statement.status is EvidenceStatus.EVIDENCED and not statement.citations:
            raise StatementWithoutCitation(statement.text)

    def assert_rejected_proposals_disclosed(self, run_rejected_measures: Sequence[str]) -> None:
        """Raise ``DisclosureMissing`` when a proposal rejected in the run is not disclosed (AC 3).

        An empty run list is a legitimate "no refusals" result and is never a missing disclosure.
        """
        disclosed = {record.measure for record in self.rejected_proposals}
        if any(measure not in disclosed for measure in run_rejected_measures):
            self.events.append(
                BriefBlockedByMissingDisclosure(self.id, (REJECTED_PROPOSALS_DISCLOSURE,))
            )
            raise DisclosureMissing(str(self.id), REJECTED_PROPOSALS_DISCLOSURE)

    def publish(self) -> None:
        """Run every gate in reading order, then freeze the artefact (AC 1-4)."""
        self.assert_immutable()
        self.status = BriefStatus.VALIDATING
        try:
            self._assert_all_sections_present()
            self._assert_statements_evidenced()
            self._assert_citations_resolved()
            self._assert_disclaimer_present()
        except AppError:
            self.status = BriefStatus.BLOCKED
            raise
        self.status = BriefStatus.PUBLISHED
        self.events.append(
            DecisionBriefPublished(
                self.id,
                self.run_id,
                self.version.number,
                len(self.sections),
                self.citation_count(),
            )
        )

    def assert_immutable(self) -> None:
        """Raise ``PublishedBriefIsImmutable`` when a published brief would change (AC 6)."""
        if self.is_published():
            raise PublishedBriefIsImmutable(str(self.id))

    def supersede_by(self, successor: DecisionBrief, *, reason: str) -> DecisionBrief:
        """Return the successor version N+1 that references this version and the reason (AC 7)."""
        raise NotImplementedError(
            "DecisionBrief.supersede_by is implemented by issue-decision-brief-lineage"
        )

    # ── publication gates (one named rule each: they are the audit trail) ──────────────

    def _assert_all_sections_present(self) -> None:
        missing = self.missing_sections()
        if missing:
            ordered = sorted(missing, key=lambda kind: SECTION_ORDINAL[kind])
            raise IncompleteBrief(ordered)

    def _assert_statements_evidenced(self) -> None:
        for section in self.sections.values():
            for statement in section.statements:
                self.assert_statement_evidence(statement)

    def _assert_citations_resolved(self) -> None:
        unresolved = self.unresolved_citations()
        if unresolved:
            first = unresolved[0]
            self.events.append(CitationResolutionFailed(self.id, len(unresolved), first.passage_id))
            raise UnresolvedCitation(str(self.id), str(first.passage_id))

    def _assert_disclaimer_present(self) -> None:
        if self.disclaimer is None:
            self.events.append(BriefBlockedByMissingDisclosure(self.id, (DISCLAIMER_DISCLOSURE,)))
            raise DisclosureMissing(str(self.id), DISCLAIMER_DISCLOSURE)
