"""HTTP container dependency of DecisionBrief (contract frozen, issue #331).

The composition root binds ``app.state.decision_brief`` in the wiring issue. Keeping the container
shape here means the router depends on the frozen service surface, never on an adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from decision_brief.application.services import (
    GetDecisionBrief,
    ListBriefVersions,
    ListCitations,
    PublishDecisionBrief,
    VersionDecisionBrief,
)
from decision_brief.domain.errors import BriefGateUnavailable
from decision_brief.interfaces.renderer import BriefRenderer


class DecisionBriefContainer(Protocol):
    """Services exposed by the composition root."""

    publish_decision_brief: PublishDecisionBrief
    version_decision_brief: VersionDecisionBrief
    get_decision_brief: GetDecisionBrief
    list_brief_versions: ListBriefVersions
    list_citations: ListCitations
    renderer: BriefRenderer


@dataclass(frozen=True, slots=True)
class ContainerView:
    container: DecisionBriefContainer


def get_container(request: Request) -> DecisionBriefContainer:
    container = getattr(request.app.state, "decision_brief", None)
    if container is None:
        raise BriefGateUnavailable("decision_brief container is not mounted")
    return container  # type: ignore[no-any-return]
