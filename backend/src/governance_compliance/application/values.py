"""Frozen vocabulary of GovernanceCompliance (contract freeze, issue #248).

Service depth (ADR-008): these are contract values and DTO fields, not domain aggregates.
Canonical: .pi/architecture/modules/governance-compliance.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NewType

ViolationId = NewType("ViolationId", str)
InvocationId = NewType("InvocationId", str)
RunId = NewType("RunId", str)
PositionId = NewType("PositionId", str)
RuleVersion = NewType("RuleVersion", str)


class GuardDecision(StrEnum):
    """The only three outcomes of the pre-persistence guard."""

    ACCEPT = "accept"
    REWRITE = "rewrite"
    REJECT = "reject"


class ViolationClass(StrEnum):
    """Stable machine-readable reason for a non-accept verdict."""

    PERSON_NAMED = "person_named"
    PERSONAL_QUOTATION = "personal_quotation"
    INSTITUTION_AMBIGUOUS = "institution_ambiguous"
    UNSUPPORTED_FACT = "unsupported_fact"
    CONTRADICTED_FIGURE = "contradicted_figure"


class SpeakerKind(StrEnum):
    """Attribution class mapped from EvidenceCorpus at the ACL boundary."""

    INSTITUTION = "institution"
    PERSON = "person"
    ANONYMOUS = "anonymous"


class FigureVerdict(StrEnum):
    """The ClaimValidation verdict subset the figure rule consumes."""

    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"


class GuardRuleId(StrEnum):
    """Deterministic rule identifiers. The value is persisted on every violation."""

    GC_001 = "GC-001"
    GC_002 = "GC-002"
    GC_003 = "GC-003"
    GC_004 = "GC-004"
    GC_005 = "GC-005"


@dataclass(frozen=True, slots=True)
class TextSpan:
    """Half-open ``[start, end)`` character span in the guarded text."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("span start must not be negative")
        if self.end <= self.start:
            raise ValueError("span end must be greater than start")


@dataclass(frozen=True, slots=True)
class PersonReference:
    """One person mention detected by the NER adapter."""

    text: str
    span: TextSpan
    title: str | None = None
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class AllowlistEntry:
    """One canonical institution and its aliases; never a natural person."""

    code: str
    canonical_name: str
    short_name: str
    category: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InstitutionalAllowlist:
    """The operator-curated allowlist loaded at boot. Empty is a boot failure."""

    institutions: tuple[AllowlistEntry, ...] = ()
    version: str = "v1"

    @property
    def is_empty(self) -> bool:
        return not self.institutions

    @property
    def canonical_names(self) -> tuple[str, ...]:
        return tuple(entry.canonical_name for entry in self.institutions)

    @property
    def aliases(self) -> dict[str, str]:
        """Map every alias and canonical name to its canonical institution name."""
        mapping: dict[str, str] = {}
        for entry in self.institutions:
            mapping[entry.canonical_name] = entry.canonical_name
            mapping[entry.short_name] = entry.canonical_name
            for alias in entry.aliases:
                mapping[alias] = entry.canonical_name
        return mapping
