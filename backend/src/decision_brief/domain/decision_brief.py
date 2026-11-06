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
from dataclasses import dataclass, field, replace
from typing import Any

from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.errors import (
    BriefNotPublished,
    BriefVersionConflict,
    DisclosureMissing,
    IncompleteBrief,
    PublishedBriefIsImmutable,
    UnresolvedCitation,
)
from decision_brief.domain.events import (
    BriefBlockedByMissingDisclosure,
    CitationResolutionFailed,
    DecisionBriefPublished,
    DecisionBriefVersioned,
    DomainEvent,
    RejectedProposalDisclosed,
)
from decision_brief.domain.values import (
    REQUIRED_SECTIONS,
    SECTION_ORDINAL,
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
from shared.errors import AppError

DISCLAIMER_DISCLOSURE = "simulation_disclaimer"
REJECTED_PROPOSALS_DISCLOSURE = "rejected_proposals"


class _FrozenSections(dict[SectionKind, BriefSection]):
    """The section map of a published brief: every mutation raises the domain error.

    ``dict`` is the frozen field type, so the guard is a subclass rather than a wrapper — a caller
    can read it exactly like a mapping and still cannot slip a section in after publication.
    """

    def __init__(self, sections: dict[SectionKind, BriefSection], brief_id: str) -> None:
        super().__init__(sections)
        self._brief_id = brief_id

    def _refuse(self) -> None:
        raise PublishedBriefIsImmutable(self._brief_id)

    def __setitem__(self, *args: object) -> None:
        self._refuse()

    def __delitem__(self, *args: object) -> None:
        self._refuse()

    def clear(self) -> None:
        self._refuse()

    def pop(self, *args: object) -> Any:
        self._refuse()

    def popitem(self) -> Any:
        self._refuse()

    def setdefault(self, *args: object) -> Any:
        self._refuse()

    def update(self, *args: object, **kwargs: object) -> None:
        self._refuse()


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

    def __setattr__(self, name: str, value: object) -> None:
        """A published version is read-only; the audit event list stays appendable."""
        if name != "events" and getattr(self, "status", None) is BriefStatus.PUBLISHED:
            raise PublishedBriefIsImmutable(str(getattr(self, "id", "unknown")))
        object.__setattr__(self, name, value)

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

    def resolve_citations(self, resolved: Sequence[CitationReference]) -> None:
        """Apply resolved citations by passage id; anything absent stays unresolved (AC 2).

        The citation gate does not invent provenance: it only folds what the resolver returned into
        the statements, which is why an unresolved passage still blocks ``publish`` afterwards.
        """
        self.assert_immutable()
        by_passage = {str(citation.passage_id): citation for citation in resolved}
        for kind, section in tuple(self.sections.items()):
            statements = tuple(
                replace(
                    statement,
                    citations=tuple(
                        by_passage.get(str(citation.passage_id), citation)
                        for citation in statement.citations
                    ),
                )
                for statement in section.statements
            )
            self.sections[kind] = replace(section, statements=statements)

    def assert_statement_evidence(self, statement: CitedStatement) -> None:
        """Raise ``StatementWithoutCitation`` for an evidenced statement with no citation (AC 5)."""
        statement.assert_evidence()

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
            self._assert_outcomes_honest()
        except AppError:
            self.status = BriefStatus.BLOCKED
            raise
        object.__setattr__(self, "sections", _FrozenSections(self.sections, str(self.id)))
        self.status = BriefStatus.PUBLISHED
        for record in self.rejected_proposals:
            self.events.append(
                RejectedProposalDisclosed(self.id, record.measure, record.blocking_stakeholders)
            )
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
        """Mark this version superseded by N+1 and return the successor (AC 7).

        The prior version keeps its content and stays retrievable; only its lifecycle moves. A
        successor is accepted only when it is the next version of the same run and names this
        version as its predecessor.
        """
        if not self.is_published():
            raise BriefNotPublished(
                f"brief {self.id} must be published before it can be superseded"
            )
        if successor.run_id != self.run_id:
            raise BriefVersionConflict(self.version.number + 1, successor.version.number)
        if (
            successor.version.number != self.version.number + 1
            or successor.version.previous_version != self.version.number
            or successor.version.reason != reason
        ):
            raise BriefVersionConflict(self.version.number + 1, successor.version.number)
        # The lifecycle transition is the one legal change to a published version.
        object.__setattr__(self, "status", BriefStatus.SUPERSEDED)
        self.events.append(DecisionBriefVersioned(successor.id, self.version.number, reason))
        return successor

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

    def _assert_outcomes_honest(self) -> None:
        for outcome in self.outcomes:
            outcome.assert_honest()

    def _assert_disclaimer_present(self) -> None:
        if self.disclaimer is None:
            self.events.append(BriefBlockedByMissingDisclosure(self.id, (DISCLAIMER_DISCLOSURE,)))
            raise DisclosureMissing(str(self.id), DISCLAIMER_DISCLOSURE)
