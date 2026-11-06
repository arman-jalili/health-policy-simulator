"""Use-case results and gate inputs of DecisionBrief (contract frozen, issue #331).

HTTP schemas are rendered from these; ``CitationResolution`` is what the citation gate consumes.
"""

from __future__ import annotations

from dataclasses import dataclass

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.values import BriefId, CitationReference, PassageId, SectionKind


@dataclass(frozen=True, slots=True)
class CitationResolution:
    """Outcome of resolving every passage id a brief cites, in input order."""

    resolved: tuple[CitationReference, ...] = ()
    unresolved: tuple[PassageId, ...] = ()

    @property
    def is_complete(self) -> bool:
        """Whether every citation resolved; publication proceeds only when true."""
        return not self.unresolved


@dataclass(frozen=True, slots=True)
class BriefResult:
    """A frozen brief plus the citation count the publication response reports."""

    brief: DecisionBrief
    citation_count: int


@dataclass(frozen=True, slots=True)
class BriefListResult:
    items: tuple[BriefResult, ...]


@dataclass(frozen=True, slots=True)
class CitationListResult:
    brief_id: BriefId
    section: SectionKind | None
    citations: tuple[CitationReference, ...]
