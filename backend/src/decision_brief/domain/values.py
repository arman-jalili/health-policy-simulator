"""Frozen value objects and enums of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Entities and value objects)

The eight section kinds, their ordinals and the evidence vocabulary are the wire contract of the
artefact: changing a member, a field name or an ordinal re-opens this freeze. Values validate
nothing here — implementation issues add the guards the invariants require.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Final, NewType

BriefId = NewType("BriefId", str)
RunId = NewType("RunId", str)
PassageId = NewType("PassageId", str)


class SectionKind(StrEnum):
    """One of the eight mandated brief components; the value is the wire name."""

    QUESTION = "question_summary"
    ACTORS = "actors_involved"
    HISTORY = "negotiation_history"
    CONFLICTS = "conflict_analysis"
    COMPROMISES = "compromise_proposals"
    CONSENSUS = "consensus_analysis"
    OPEN_DISPUTES = "open_disputes"
    IMPACT = "impact"


SECTION_ORDINAL: Final[Mapping[SectionKind, int]] = MappingProxyType(
    {
        SectionKind.QUESTION: 1,
        SectionKind.ACTORS: 2,
        SectionKind.HISTORY: 3,
        SectionKind.CONFLICTS: 4,
        SectionKind.COMPROMISES: 5,
        SectionKind.CONSENSUS: 6,
        SectionKind.OPEN_DISPUTES: 7,
        SectionKind.IMPACT: 8,
    }
)
"""Reading order of the artefact; the ordinal is part of the published document."""

REQUIRED_SECTIONS: Final[frozenset[SectionKind]] = frozenset(SectionKind)
"""Publication requires exactly these; a missing kind is named in ``IncompleteBrief``."""


class EvidenceStatus(StrEnum):
    """Whether a statement carries evidence, is narrative, or is explicitly unsupported."""

    EVIDENCED = "evidenced"
    NARRATIVE = "narrative"
    UNSUPPORTED = "unsupported"


class BriefStatus(StrEnum):
    """Lifecycle of the artefact; ``PUBLISHED`` is immutable."""

    DRAFT = "draft"
    VALIDATING = "validating"
    BLOCKED = "blocked"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"


class OutcomeKind(StrEnum):
    """How a topic outcome may be rendered; a veto-blocked topic is never a recommendation."""

    RECOMMENDATION = "recommendation"
    BLOCKED = "blocked"
    OPEN_DISPUTE = "open_dispute"


@dataclass(frozen=True, slots=True)
class CitationProvenance:
    """Locator a reader can open to verify a citation (conformist mirror of the corpus view)."""

    outlet: str
    published_on: date
    medium: str
    page_from: int
    page_to: int
    source_uri: str


@dataclass(frozen=True, slots=True)
class CitationReference:
    """Resolvable pointer from a statement to a passage provenance, with resolution state."""

    passage_id: PassageId
    provenance: CitationProvenance | None = None
    quote: str | None = None

    def is_resolved(self) -> bool:
        """A citation is resolved only when the target passage provenance is present."""
        return self.provenance is not None


@dataclass(frozen=True, slots=True)
class CitedStatement:
    """Statement + citations + source claim ids + evidence status; equal by content."""

    text: str
    status: EvidenceStatus
    citations: tuple[CitationReference, ...] = ()
    claim_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BriefVersion:
    """Version marker tying the artefact to run, snapshot, generation time and lineage."""

    number: int
    run_id: RunId
    snapshot_ref: str
    generated_at: datetime
    previous_version: int | None = None
    reason: str | None = None


DEFAULT_DISCLAIMER_TEXT: Final[str] = (
    "This brief reports probabilistic reasoning over a pinned corpus snapshot. "
    "It is not a deterministic forecast and must not be read as established fact."
)
"""Fixed disclosure wording; the model and prompt reference are carried beside it."""


@dataclass(frozen=True, slots=True)
class SimulationDisclaimer:
    """Statement that results are probabilistic reasoning over a pinned corpus (invariant 4)."""

    text: str
    model_reference: str
    prompt_version: str


@dataclass(frozen=True, slots=True)
class ActorSummary:
    """Institution, goals, constraints and adopted positions shown in section 2."""

    institution: str
    goals: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    adopted_positions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PositionStance:
    """One recorded stance in a change visualisation."""

    round_no: int
    stance: str
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class PositionTimeline:
    """Stance trajectory across rounds for one actor."""

    actor: str
    stances: tuple[PositionStance, ...] = ()


@dataclass(frozen=True, slots=True)
class BriefComponentSlot:
    """Ordinal and completion state of one mandated component."""

    kind: SectionKind
    ordinal: int
    completed: bool = False


@dataclass(frozen=True, slots=True)
class TopicOutcome:
    """How one topic is stated: recommendation, blocked or still disputed (invariant 8)."""

    topic: str
    kind: OutcomeKind
    blocking_stakeholders: tuple[str, ...] = ()
    reason: str | None = None
