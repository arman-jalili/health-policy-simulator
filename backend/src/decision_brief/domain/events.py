"""Domain events of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Domain Events)

Payloads are frozen: every event names ids and counts, never a rendered document. Publication,
versioning and every blocked publication travel through the shared outbox (ADR-002).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from decision_brief.domain.values import BriefId, PassageId, RunId


@dataclass(frozen=True, slots=True)
class DecisionBriefPublished:
    """Complete, citation-resolved brief published."""

    name: ClassVar[str] = "DecisionBriefPublished"
    brief_id: BriefId
    run_id: RunId
    version: int
    section_count: int
    citation_count: int


@dataclass(frozen=True, slots=True)
class DecisionBriefVersioned:
    """Successor version produced for the same run; lineage is explicit."""

    name: ClassVar[str] = "DecisionBriefVersioned"
    brief_id: BriefId
    previous_version: int
    reason: str


@dataclass(frozen=True, slots=True)
class CitationResolutionFailed:
    """A citation could not be resolved; publication was blocked."""

    name: ClassVar[str] = "CitationResolutionFailed"
    brief_id: BriefId
    unresolved_count: int
    first_passage_id: PassageId | None = None


@dataclass(frozen=True, slots=True)
class RejectedProposalDisclosed:
    """Rejected proposal disclosed with its blockers (invariant 6)."""

    name: ClassVar[str] = "RejectedProposalDisclosed"
    brief_id: BriefId
    measure: str
    blocker_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BriefBlockedByMissingDisclosure:
    """Publication refused for one or more missing required disclosures."""

    name: ClassVar[str] = "BriefBlockedByMissingDisclosure"
    brief_id: BriefId
    missing: tuple[str, ...] = ()


DomainEvent = (
    DecisionBriefPublished
    | DecisionBriefVersioned
    | CitationResolutionFailed
    | RejectedProposalDisclosed
    | BriefBlockedByMissingDisclosure
)
