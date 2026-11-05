"""Frozen value objects and enums of the EvidenceRetrieval bounded context.

Canonical: .pi/architecture/modules/evidence-retrieval.md

CONTRACT FREEZE — names, field sets and invariants below are the published contract. Retrieval
must never invent its own authority rubric: authority tiers come from EvidenceCorpus and the weight
is looked up through :class:`PassageSearchPort`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, NewType

from evidence_corpus.domain.values import AuthorityRule, AuthorityTier, ClaimType, SourceType

PackId = NewType("PackId", str)
"""Identity of one frozen evidence pack (``evp_...``)."""

ClaimText = NewType("ClaimText", str)
"""The claim a pack is assembled for; preserved verbatim for traceability."""

SnapshotId = NewType("SnapshotId", str)
"""Corpus snapshot the retrieval was pinned to (reproducibility invariant 5)."""

PassageId = NewType("PassageId", str)
"""EvidenceCorpus passage identity; retrieval stores refs, never corpus rows."""

DEFAULT_RESULT_LIMIT: Final[int] = 20


class StanceLabel(StrEnum):
    """Whether a passage supports, contradicts, contextualises or is tangential to a claim."""

    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONTEXTUAL = "contextual"
    TANGENTIAL = "tangential"


@dataclass(frozen=True, slots=True)
class StanceAssessment:
    """A stance label plus the evidence that makes the passage direct or merely topical."""

    label: StanceLabel
    directness: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.directness <= 1.0:
            raise ValueError("StanceAssessment.directness must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class EvidenceScore:
    """Inspectable multi-component weighting; equal by components (ADR-008).

    ``final`` is reproducible from the five components (their sum). Components are the weighted
    contributions, so ``final`` is not clamped to ``[0, 1]``.
    """

    authority: float
    lexical: float
    semantic: float
    recency: float
    directness: float
    final: float

    def __post_init__(self) -> None:
        for name in ("authority", "lexical", "semantic", "recency", "directness"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"EvidenceScore.{name} must be within [0, 1]")
        if not math.isclose(self.final, self.component_sum, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("EvidenceScore.final must equal the sum of its components")

    @property
    def component_sum(self) -> float:
        """Return the sum the final score must reproduce."""
        return self.authority + self.lexical + self.semantic + self.recency + self.directness


DEFAULT_RECENCY_EXEMPTIONS: Final[frozenset[SourceType]] = frozenset({SourceType.LEGISLATION})
"""Non-perishable source types keep full recency weight (invariant 7)."""


@dataclass(frozen=True, slots=True)
class RecencyPolicy:
    """Configured exponential decay with explicit exemptions for non-perishable sources."""

    half_life_days: float = 365.0
    exempt_source_types: frozenset[SourceType] = DEFAULT_RECENCY_EXEMPTIONS

    def __post_init__(self) -> None:
        if self.half_life_days <= 0:
            raise ValueError("RecencyPolicy.half_life_days must be positive")

    def is_exempt(self, source_type: SourceType) -> bool:
        """Return whether ``source_type`` is non-perishable under this policy."""
        return source_type in self.exempt_source_types


@dataclass(frozen=True, slots=True)
class AuthorityWeight:
    """Numeric weight derived from the corpus rubric for one source tier."""

    tier: AuthorityTier
    weight: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("AuthorityWeight.weight must be within [0, 1]")

    @classmethod
    def from_rule(cls, rule: AuthorityRule, tier: AuthorityTier) -> AuthorityWeight:
        """Derive the weight from the corpus rule; retrieval never owns a rubric.

        The tier is mapped to the corpus source-type vocabulary and positioned in the rule's
        ordering. The top source gets ``1.0``; lower positions decay linearly.
        """
        source_type = SourceType(tier.value)
        if source_type not in rule.ordered_source_types:
            raise ValueError(f"tier {tier.value!r} is not in the corpus rule")
        position = rule.ordered_source_types.index(source_type)
        return cls(
            tier=tier,
            weight=(len(rule.ordered_source_types) - position) / len(rule.ordered_source_types),
        )


@dataclass(frozen=True, slots=True)
class QueryRewrite:
    """Deterministic German expansion of a claim query: compounds, umlauts, synonyms."""

    original: str
    expanded: str

    def __post_init__(self) -> None:
        if not self.original.strip():
            raise ValueError("QueryRewrite.original must be non-empty")
        if not self.expanded.strip():
            raise ValueError("QueryRewrite.expanded must be non-empty")


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Input to a search operation; no lifecycle, so it remains a value object."""

    claim: ClaimText
    claim_type: ClaimType
    snapshot_id: SnapshotId
    limit: int = DEFAULT_RESULT_LIMIT

    def __post_init__(self) -> None:
        if not self.claim.strip():
            raise ValueError("RetrievalQuery.claim must be non-empty")
        if self.limit < 1:
            raise ValueError("RetrievalQuery.limit must be at least 1")


@dataclass(frozen=True, slots=True)
class AbsenceFinding:
    """A truthful "searched, found nothing" record: queries, snapshot and reason."""

    queries: tuple[str, ...]
    snapshot_id: SnapshotId
    reason: str

    def __post_init__(self) -> None:
        if not self.queries:
            raise ValueError("AbsenceFinding.queries must name at least one search")
        if not all(query.strip() for query in self.queries):
            raise ValueError("AbsenceFinding.queries must not contain empty queries")
        if not self.reason.strip():
            raise ValueError("AbsenceFinding.reason must be non-empty")


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Derived measurement of availability per stance and the best authority found."""

    stance_counts: Mapping[StanceLabel, int]
    best_authority: AuthorityWeight | None = None

    @property
    def total(self) -> int:
        """Return the total number of candidates counted across stances."""
        return sum(self.stance_counts.values())
