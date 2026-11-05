"""Frozen value objects and enums of the EvidenceCorpus bounded context.

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — this module declares shapes, not behaviour. Validation that enforces the module
invariants is added by the implementation issues that follow; the signatures and the rubric data
below are frozen. Changing a member, a field name or a rubric order requires re-opening the contract
issue.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from types import MappingProxyType
from typing import Final

# ── Extraction ────────────────────────────────────────────────────────────────


class ExtractionMethod(StrEnum):
    """How the text of a Document was obtained."""

    NATIVE = "native"
    OCR = "ocr"


@dataclass(frozen=True, slots=True)
class PageTextFacts:
    """Page-level measurements used to select an extraction route.

    Input to :class:`NativeVsOcrSelection`; produced by an :class:`ExtractionPort` probe.
    """

    has_text_layer: bool
    average_chars_per_page: float
    missing_glyph_rate: float


@dataclass(frozen=True, slots=True)
class ExtractionQuality:
    """Measured fidelity of extracted text. A measurement, never an opinion."""

    method: ExtractionMethod
    confidence: float
    missing_glyph_rate: float
    page_count: int = 1

    def is_acceptable(self, minimum_confidence: float = 0.85) -> bool:
        """Whether this extraction may produce citable passages (invariant 4).

        Both signals must hold: enough confidence in the text, and little glyph damage. A high
        confidence on a badly damaged scan is still unusable evidence.
        """
        return (
            self.page_count > 0
            and self.confidence >= minimum_confidence
            and self.missing_glyph_rate <= MAX_MISSING_GLYPH_RATE
        )


DEFAULT_MINIMUM_CONFIDENCE: Final[float] = 0.85
MAX_MISSING_GLYPH_RATE: Final[float] = 0.15


# ── Text geometry ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Offsets:
    """Half-open `[start, end)` span into the parent Article body.

    Intrinsic sanity is enforced here; containment in the parent article and sibling overlap are
    enforced by the aggregate (`Document.add_article` / `Article.add_passage`), which own the text.
    """

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("offset start must not be negative")
        if self.end <= self.start:
            raise ValueError("offset end must be greater than start")

    @property
    def length(self) -> int:
        return self.end - self.start

    def overlaps(self, other: Offsets) -> bool:
        """Half-open intervals overlap when each starts before the other ends."""
        return self.start < other.end and other.start < self.end

    def within(self, article_length: int) -> bool:
        return self.start >= 0 and self.end <= article_length


class ArticleSection(StrEnum):
    """Typed region label of an Article."""

    HEADLINE = "headline"
    STANDFIRST = "standfirst"
    BODY = "body"
    CAPTION = "caption"
    QUOTATION = "quotation"


@dataclass(frozen=True, slots=True)
class LanguageTag:
    """BCP-47 language tag, e.g. `de-AT`."""

    tag: str


LANGUAGE_DE_AT: Final[LanguageTag] = LanguageTag("de-AT")


@dataclass(frozen=True, slots=True)
class ArticleDraft:
    """One editorial unit proposed by an :class:`ArticleBoundaryStrategy`.

    A draft is not yet an Article: the Document aggregate assigns identity and validates bounds.
    """

    headline: str
    body: str
    page_from: int
    page_to: int


# ── Citation provenance ───────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Provenance:
    """Immutable locator bundle: the citation target a reader can open and verify."""

    outlet: str
    published_on: date
    medium: str
    page_from: int
    page_to: int
    offsets: Offsets
    source_uri: str


class SpeakerKind(StrEnum):
    """Attribution class of a statement; decides citability (invariant 5)."""

    INSTITUTION = "institution"
    PERSON = "person"
    ANONYMOUS = "anonymous"


CITABLE_SPEAKER_KINDS: Final[frozenset[SpeakerKind]] = frozenset({SpeakerKind.INSTITUTION})


@dataclass(frozen=True, slots=True)
class QuotationBlock:
    """Quoted or reported speech retained structurally but never promoted to evidence."""

    text: str
    speaker_kind: SpeakerKind
    offsets: Offsets


@dataclass(frozen=True, slots=True)
class CanonicalArticleRef:
    """Pointer to the article that owns citations when syndicated copies exist."""

    canonical_article_id: str
    similarity: float


# ── Authority rubric ──────────────────────────────────────────────────────────


class AuthorityTier(StrEnum):
    """Ranked credibility rubric position owned by the corpus.

    Identity is the tier name, not an instance; retrieval consumes it instead of redefining trust.
    """

    OFFICIAL_STATISTICS = "official_statistics"
    LEGISLATION = "legislation"
    SCIENTIFIC_STUDY = "scientific_study"
    INSTITUTIONAL_STATEMENT = "institutional_statement"
    PRESS_REPORT = "press_report"
    OTHER = "other"


class SourceType(StrEnum):
    """Source type declared by the operator at ingestion (invariant 7).

    Shares vocabulary with :class:`AuthorityTier` by design: a *declared* type can be refused
    (`unknown`), whereas an *assigned* tier cannot. Keeping them separate makes that asymmetry
    expressible in the type system.
    """

    OFFICIAL_STATISTICS = "official_statistics"
    LEGISLATION = "legislation"
    SCIENTIFIC_STUDY = "scientific_study"
    INSTITUTIONAL_STATEMENT = "institutional_statement"
    PRESS_REPORT = "press_report"
    OTHER = "other"
    UNKNOWN = "unknown"


class ClaimType(StrEnum):
    """Claim-type vocabulary used to select an :class:`AuthorityRule`.

    ClaimValidation owns the semantics; the corpus owns the rubric that ranks sources per type.
    The member set is frozen as published language between the two contexts.
    """

    QUANTITATIVE = "quantitative"
    LEGAL = "legal"
    CAUSAL = "causal"
    QUALITATIVE = "qualitative"


@dataclass(frozen=True, slots=True)
class AuthorityRule:
    """Claim-type-specific ordering of source types (replaces a single global scale)."""

    claim_type: ClaimType
    ordered_source_types: tuple[SourceType, ...]


AUTHORITY_RULES: Final[Mapping[ClaimType, tuple[SourceType, ...]]] = MappingProxyType(
    {
        ClaimType.LEGAL: (
            SourceType.LEGISLATION,
            SourceType.OFFICIAL_STATISTICS,
            SourceType.SCIENTIFIC_STUDY,
            SourceType.INSTITUTIONAL_STATEMENT,
            SourceType.PRESS_REPORT,
            SourceType.OTHER,
        ),
        ClaimType.QUANTITATIVE: (
            SourceType.OFFICIAL_STATISTICS,
            SourceType.SCIENTIFIC_STUDY,
            SourceType.LEGISLATION,
            SourceType.INSTITUTIONAL_STATEMENT,
            SourceType.PRESS_REPORT,
            SourceType.OTHER,
        ),
        ClaimType.CAUSAL: (
            SourceType.SCIENTIFIC_STUDY,
            SourceType.OFFICIAL_STATISTICS,
            SourceType.LEGISLATION,
            SourceType.INSTITUTIONAL_STATEMENT,
            SourceType.PRESS_REPORT,
            SourceType.OTHER,
        ),
        ClaimType.QUALITATIVE: (
            SourceType.INSTITUTIONAL_STATEMENT,
            SourceType.LEGISLATION,
            SourceType.SCIENTIFIC_STUDY,
            SourceType.OFFICIAL_STATISTICS,
            SourceType.PRESS_REPORT,
            SourceType.OTHER,
        ),
    }
)
"""Frozen rubric: press reporting never outranks an authoritative source type."""


def authority_rule(claim_type: ClaimType) -> AuthorityRule:
    """Return the frozen authority rule for ``claim_type``."""
    return AuthorityRule(claim_type=claim_type, ordered_source_types=AUTHORITY_RULES[claim_type])
