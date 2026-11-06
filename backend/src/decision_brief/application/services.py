"""Frozen application services of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Service classification, API Endpoints)

Constructors, service names and ``execute`` signatures are frozen. Every use case below is
implemented; later issues may not rename or remove a frozen member without a new freeze entry.

``collaborators`` is the published wiring contract of each use case: it names every port the
composition root must supply, and it is what keeps the W8 reachability gate honest while the bodies
are still stubs.
"""

from __future__ import annotations

from decision_brief.application.commands import (
    GetDecisionBriefRequest,
    ListBriefVersionsRequest,
    ListCitationsRequest,
    PublishDecisionBriefRequest,
    VersionDecisionBriefRequest,
)
from decision_brief.application.dto import BriefListResult, BriefResult, CitationListResult
from decision_brief.application.ports import (
    CitationResolver,
    Clock,
    ConsensusSource,
    EventPublisher,
    IdFactory,
    ProvenanceDisclosureGate,
    RunHistorySource,
    UnitOfWork,
)
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.errors import (
    BriefNotFound,
    BriefNotPublished,
    BriefSourceIncomplete,
)
from decision_brief.domain.repositories import DecisionBriefRepository
from decision_brief.domain.services import BriefProjectionBuilder
from decision_brief.domain.values import (
    BriefId,
    BriefStatus,
    BriefVersion,
    SimulationDisclaimer,
)


class PublishDecisionBrief:
    """Transaction boundary: build the eight sections, run every gate, freeze the version."""

    def __init__(
        self,
        *,
        briefs: DecisionBriefRepository,
        history: RunHistorySource,
        consensus: ConsensusSource,
        citations: CitationResolver,
        provenance: ProvenanceDisclosureGate,
        projection: BriefProjectionBuilder,
        disclaimer: SimulationDisclaimer,
        events: EventPublisher,
        clock: Clock,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._briefs = briefs
        self._history = history
        self._consensus = consensus
        self._citations = citations
        self._provenance = provenance
        self._projection = projection
        self._disclaimer = disclaimer
        self._events = events
        self._clock = clock
        self._ids = ids
        self._uow = uow

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (
            self._briefs,
            self._history,
            self._consensus,
            self._citations,
            self._provenance,
            self._projection,
            self._disclaimer,
            self._events,
            self._clock,
            self._ids,
            self._uow,
        )

    async def execute(self, request: PublishDecisionBriefRequest) -> BriefResult:
        run = await self._history.load(request.run_id)
        if run is None:
            raise BriefSourceIncomplete(str(request.run_id), "closed run history")
        consensus = await self._consensus.load(request.run_id)
        if consensus is None:
            raise BriefSourceIncomplete(str(request.run_id), "derived consensus")
        await self._provenance.assert_disclosed(request.run_id)
        brief = self._projection.build(run=run, consensus=consensus, disclaimer=self._disclaimer)
        brief.assert_rejected_proposals_disclosed(
            [record.measure for record in run.rejected_proposals]
        )
        passage_ids = tuple(
            dict.fromkeys(
                citation.passage_id
                for section in brief.sections.values()
                for statement in section.statements
                for citation in statement.citations
            )
        )
        resolution = await self._citations.resolve(passage_ids)
        brief.resolve_citations(resolution.resolved)
        brief.publish()
        async with self._uow.transaction():
            await self._briefs.save(brief)
            await self._events.publish(brief.events)
        return BriefResult(brief=brief, citation_count=brief.citation_count())


class VersionDecisionBrief:
    """Create a successor version N+1 that references N and carries the reason (AC 7)."""

    def __init__(
        self,
        *,
        briefs: DecisionBriefRepository,
        events: EventPublisher,
        clock: Clock,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._briefs = briefs
        self._events = events
        self._clock = clock
        self._ids = ids
        self._uow = uow

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._briefs, self._events, self._clock, self._ids, self._uow)

    async def execute(self, request: VersionDecisionBriefRequest) -> BriefResult:
        if not request.reason.strip():
            raise ValueError("a successor version requires a reason")
        previous = await self._briefs.get(request.brief_id)
        if previous is None:
            raise BriefNotFound(f"brief {request.brief_id} was not found")
        if not previous.is_published():
            raise BriefNotPublished(
                f"brief {request.brief_id} must be published before it can be versioned"
            )
        successor = DecisionBrief(
            id=BriefId(self._ids.new_id("brf")),
            run_id=previous.run_id,
            version=BriefVersion(
                number=previous.version.number + 1,
                run_id=previous.run_id,
                snapshot_ref=previous.version.snapshot_ref,
                generated_at=self._clock.now(),
                previous_version=previous.version.number,
                reason=request.reason,
            ),
            sections=dict(previous.sections),
            rejected_proposals=previous.rejected_proposals,
            disclaimer=previous.disclaimer,
            outcomes=previous.outcomes,
        )
        successor.publish()
        async with self._uow.transaction():
            previous.supersede_by(successor, reason=request.reason)
            await self._briefs.save(previous)
            await self._briefs.save(successor)
            versioned = previous.events[-1]
            await self._events.publish([versioned, *successor.events])
        return BriefResult(brief=successor, citation_count=successor.citation_count())


class GetDecisionBrief:
    """Read one frozen brief; the read never re-derives sections."""

    def __init__(self, *, briefs: DecisionBriefRepository) -> None:
        self._briefs = briefs

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._briefs,)

    async def execute(self, request: GetDecisionBriefRequest) -> BriefResult:
        brief = await self._briefs.get(request.brief_id)
        if brief is None:
            raise BriefNotFound(f"brief {request.brief_id} was not found")
        return BriefResult(brief=brief, citation_count=brief.citation_count())


class ListBriefVersions:
    """List every version of one run, ordered by version, with lineage."""

    def __init__(self, *, briefs: DecisionBriefRepository) -> None:
        self._briefs = briefs

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._briefs,)

    async def execute(self, request: ListBriefVersionsRequest) -> BriefListResult:
        versions = await self._briefs.versions_for_run(request.run_id)
        return BriefListResult(
            items=tuple(
                BriefResult(brief=brief, citation_count=brief.citation_count())
                for brief in versions
            )
        )


class ListCitations:
    """List the citation state of one brief, optionally filtered to one section."""

    def __init__(self, *, briefs: DecisionBriefRepository) -> None:
        self._briefs = briefs

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._briefs,)

    async def execute(self, request: ListCitationsRequest) -> CitationListResult:
        brief = await self._briefs.get(request.brief_id)
        if brief is None:
            raise BriefNotFound(f"brief {request.brief_id} was not found")
        if brief.status not in (BriefStatus.PUBLISHED, BriefStatus.SUPERSEDED):
            raise BriefNotPublished(
                f"brief {request.brief_id} has no published citations to list yet"
            )
        citations = tuple(
            citation
            for section in brief.sections.values()
            if request.section is None or section.kind is request.section
            for statement in section.statements
            for citation in statement.citations
        )
        return CitationListResult(
            brief_id=request.brief_id,
            section=request.section,
            citations=citations,
        )
