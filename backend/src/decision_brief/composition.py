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
    renderer: BriefRenderer,
) -> DecisionBriefContainer:
    """Build the container; the wiring issue supplies every port and binds ``app.state``."""
    raise NotImplementedError(
        "decision-brief composition is implemented by issue-decision-brief-wiring"
    )
