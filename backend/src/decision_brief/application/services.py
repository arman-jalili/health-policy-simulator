"""Frozen application services of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Service classification, API Endpoints)

Constructors, service names and ``execute`` signatures are frozen. Bodies raise
``NotImplementedError`` naming the implementing issue; later issues may not rename or remove a
frozen member without a new freeze entry.

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
from decision_brief.domain.repositories import DecisionBriefRepository
from decision_brief.domain.services import BriefProjectionBuilder
from decision_brief.domain.values import SimulationDisclaimer


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
        raise NotImplementedError(
            "PublishDecisionBrief.execute is implemented by issue-decision-brief-eight-sections"
        )


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
        raise NotImplementedError(
            "VersionDecisionBrief.execute is implemented by issue-decision-brief-lineage"
        )


class GetDecisionBrief:
    """Read one frozen brief; the read never re-derives sections."""

    def __init__(self, *, briefs: DecisionBriefRepository) -> None:
        self._briefs = briefs

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._briefs,)

    async def execute(self, request: GetDecisionBriefRequest) -> BriefResult:
        raise NotImplementedError(
            "GetDecisionBrief.execute is implemented by issue-decision-brief-wiring"
        )


class ListBriefVersions:
    """List every version of one run, ordered by version, with lineage."""

    def __init__(self, *, briefs: DecisionBriefRepository) -> None:
        self._briefs = briefs

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._briefs,)

    async def execute(self, request: ListBriefVersionsRequest) -> BriefListResult:
        raise NotImplementedError(
            "ListBriefVersions.execute is implemented by issue-decision-brief-lineage"
        )


class ListCitations:
    """List the citation state of one brief, optionally filtered to one section."""

    def __init__(self, *, briefs: DecisionBriefRepository) -> None:
        self._briefs = briefs

    def collaborators(self) -> tuple[object, ...]:
        """Ports this use case requires (W8 reachability anchor)."""
        return (self._briefs,)

    async def execute(self, request: ListCitationsRequest) -> CitationListResult:
        raise NotImplementedError(
            "ListCitations.execute is implemented by issue-decision-brief-citation-gate"
        )
