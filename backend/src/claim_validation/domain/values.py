"""Value objects of ClaimValidation (contract frozen, issue #164).

Canonical: `.pi/architecture/modules/claim-validation.md`
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import NewType

from evidence_corpus.domain.values import AuthorityTier

ClaimId = NewType("ClaimId", str)
ReferenceFigureId = NewType("ReferenceFigureId", str)
ContradictionId = NewType("ContradictionId", str)
ReviewId = NewType("ReviewId", str)


class ClaimType(StrEnum):
    """The verification procedure a claim requires."""

    QUANTITATIVE = "quantitative"
    LEGAL = "legal"
    CAUSAL = "causal"
    QUALITATIVE = "qualitative"


class VerificationVerdict(StrEnum):
    """A claim's settled or in-flight verification state."""

    PENDING = "pending"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"


class VerificationPath(StrEnum):
    """Type-directed route; path/type mismatch is refused."""

    QUANTITATIVE = "quantitative"
    LEGAL = "legal"
    CAUSAL = "causal"
    QUALITATIVE = "qualitative"


class CausalSupport(StrEnum):
    """Study appraisal outcome; never a verified fact."""

    SUPPORTED = "supported"
    CONTESTED = "contested"
    UNADDRESSED = "unaddressed"


@dataclass(frozen=True, slots=True)
class MeasureReference:
    """Normalised figure identity: measure, unit, period and geography."""

    measure: str
    unit: str
    period: str
    geography: str

    def __post_init__(self) -> None:
        for name in ("measure", "unit", "period", "geography"):
            if not getattr(self, name).strip():
                raise ValueError(f"measure reference {name} must not be empty")


@dataclass(frozen=True, slots=True)
class ToleranceBand:
    """Relative admissible deviation below which two figures are equal."""

    relative: Decimal = Decimal("0.02")

    def __post_init__(self) -> None:
        if self.relative < 0 or self.relative > 1:
            raise ValueError("tolerance band must be between 0 and 1")

    def contains(self, asserted: Decimal, reference: Decimal) -> bool:
        """Return whether the asserted value is within the relative band."""
        if reference == 0:
            return asserted == 0
        return abs(asserted - reference) <= abs(reference) * self.relative


@dataclass(frozen=True, slots=True)
class ReferenceFigure:
    """Canonical authoritative value with tier, as-of date and source."""

    id: ReferenceFigureId
    measure: MeasureReference
    value: Decimal
    tier: AuthorityTier
    as_of: date
    source_id: str

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("reference figure value must not be negative")
        if not self.source_id.strip():
            raise ValueError("reference figure needs a source id")


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    """Inputs a type-directed verification path may consume."""

    sources: tuple[str, ...] = ()
    reference_figure: ReferenceFigure | None = None
    asserted_value: Decimal | None = None
    asserted_measure: MeasureReference | None = None
    method: str = "deterministic"
    support: CausalSupport | None = None
    study_ids: tuple[str, ...] = ()
