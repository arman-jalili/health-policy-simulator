"""Frozen composition factory of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Wiring Contract)

The factory intentionally is not called by ``shared/app.py`` until the wiring issue. It names every
dependency the runtime must provide, and every gate is a **required** keyword argument: there is no
default citation resolver and no default provenance gate, so publication cannot be booted with a
gate silently skipped (AC 11).
"""

from __future__ import annotations

from dataclasses import dataclass

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
from decision_brief.application.services import (
    GetDecisionBrief,
    ListBriefVersions,
    ListCitations,
    PublishDecisionBrief,
    VersionDecisionBrief,
)
from decision_brief.domain.repositories import DecisionBriefRepository
from decision_brief.domain.services import BriefProjectionBuilder
from decision_brief.domain.values import SimulationDisclaimer
from decision_brief.interfaces.renderer import BriefRenderer
from shared.config import Settings
from shared.db import Database
from shared.log_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DecisionBriefContainer:
    publish_decision_brief: PublishDecisionBrief
    version_decision_brief: VersionDecisionBrief
    get_decision_brief: GetDecisionBrief
    list_brief_versions: ListBriefVersions
    list_citations: ListCitations
    renderer: BriefRenderer


def build_container(
    settings: Settings,
    database: Database,
    *,
    disclaimer: SimulationDisclaimer,
    events: EventPublisher,
    clock: Clock,
    ids: IdFactory,
    uow: UnitOfWork,
    briefs: DecisionBriefRepository,
    history: RunHistorySource,
    consensus: ConsensusSource,
    citations: CitationResolver,
    provenance: ProvenanceDisclosureGate,
    projection: BriefProjectionBuilder,
    renderer: BriefRenderer,
) -> DecisionBriefContainer:
    """Build the container; the runtime supplies every port and binds ``app.state``.

    Ports the runtime has not bound yet are replaced by fail-closed stand-ins, so a publication
    attempt raises ``BRIEF_GATE_UNAVAILABLE`` instead of skipping a gate. The repository is
    in-memory until migration ``0502`` gets its SQLAlchemy adapter (runtime-integration issue).
    """
    del database  # configuration is validated by the app shell

    logger.info(
        "decision_brief_wired",
        persistence=settings.persistence.value,
        citations=type(citations).__name__,
        provenance=type(provenance).__name__,
        projection=type(projection).__name__,
        repository=type(briefs).__name__,
    )
    return DecisionBriefContainer(
        publish_decision_brief=PublishDecisionBrief(
            briefs=briefs,
            history=history,
            consensus=consensus,
            citations=citations,
            provenance=provenance,
            projection=projection,
            disclaimer=disclaimer,
            events=events,
            clock=clock,
            ids=ids,
            uow=uow,
        ),
        version_decision_brief=VersionDecisionBrief(
            briefs=briefs,
            events=events,
            clock=clock,
            ids=ids,
            uow=uow,
        ),
        get_decision_brief=GetDecisionBrief(briefs=briefs),
        list_brief_versions=ListBriefVersions(briefs=briefs),
        list_citations=ListCitations(briefs=briefs),
        renderer=renderer,
    )
