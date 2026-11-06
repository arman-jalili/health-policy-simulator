"""Use-case request DTOs of DecisionBrief (contract frozen, issue #331)."""

from __future__ import annotations

from dataclasses import dataclass

from decision_brief.domain.values import BriefId, RunId, SectionKind


@dataclass(frozen=True, slots=True)
class PublishDecisionBriefRequest:
    """Publish the brief of a closed run; sections are built from projections, not supplied."""

    run_id: RunId
    requested_by: str | None = None


@dataclass(frozen=True, slots=True)
class VersionDecisionBriefRequest:
    """Create the successor of a published brief; the reason is mandatory lineage."""

    brief_id: BriefId
    reason: str
    requested_by: str | None = None


@dataclass(frozen=True, slots=True)
class GetDecisionBriefRequest:
    brief_id: BriefId


@dataclass(frozen=True, slots=True)
class ListBriefVersionsRequest:
    run_id: RunId


@dataclass(frozen=True, slots=True)
class ListCitationsRequest:
    brief_id: BriefId
    section: SectionKind | None = None
