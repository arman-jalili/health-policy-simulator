"""Value objects and enums of DecisionBrief (contract frozen #331, validated by #333).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Entities and value objects)

The eight section kinds, their ordinals and the evidence vocabulary are the wire contract of the
artefact: changing a member, a field name or an ordinal re-opens this freeze. A value that exists is
a value that is valid: every object below rejects the degenerate form that would make the artefact
dishonest or unopenable (empty text, a missing generation reference, a version that cannot be a
successor, a section in the wrong place).
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

    def __post_init__(self) -> None:
        if not self.outlet.strip():
            raise ValueError("citation provenance requires an outlet")
        if not self.source_uri.strip():
            raise ValueError("citation provenance requires a source URI")
        if self.page_from < 1:
            raise ValueError("citation page numbers are 1-based")
        if self.page_to < self.page_from:
            raise ValueError("citation page_to must not precede page_from")


@dataclass(frozen=True, slots=True)
class CitationReference:
    """Resolvable pointer from a statement to a passage provenance, with resolution state."""

    passage_id: PassageId
    provenance: CitationProvenance | None = None
    quote: str | None = None

    def __post_init__(self) -> None:
        if not str(self.passage_id).strip():
            raise ValueError("a citation reference requires a passage id")
        if self.quote is not None and not self.quote.strip():
            raise ValueError("a citation quote must not be blank when present")

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

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("a cited statement requires text")

    @property
    def is_evidenced(self) -> bool:
        """Whether this statement claims to be backed by evidence."""
        return self.status is EvidenceStatus.EVIDENCED

    def assert_evidence(self) -> None:
        """Refuse a statement that claims evidence without citing a passage (invariant 5).

        Claim ids are a lookup hint, not proof: they never substitute for a citation, which is why
        this rule only looks at ``citations``.
        """
        from decision_brief.domain.errors import StatementWithoutCitation

        if self.is_evidenced and not self.citations:
            raise StatementWithoutCitation(self.text)


@dataclass(frozen=True, slots=True)
class BriefVersion:
    """Version marker tying the artefact to run, snapshot, generation time and lineage."""

    number: int
    run_id: RunId
    snapshot_ref: str
    generated_at: datetime
    previous_version: int | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("a brief version number starts at 1")
        if not self.snapshot_ref.strip():
            raise ValueError("a brief version must pin the corpus snapshot it was built from")
        if self.generated_at.tzinfo is None:
            raise ValueError("a brief version requires a timezone-aware generation time")
        if self.previous_version is not None:
            if self.previous_version < 1 or self.previous_version >= self.number:
                raise ValueError("a successor must reference an earlier version")
            if self.reason is None or not self.reason.strip():
                raise ValueError("a successor version requires a reason")
        elif self.reason is not None:
            raise ValueError("only a successor version carries a reason")


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

    @classmethod
    def canonical(cls, *, model_reference: str, prompt_version: str) -> SimulationDisclaimer:
        """Build the mandatory disclosure with the frozen wording (never a free-form caveat).

        The model and prompt reference are required: a disclaimer without them would state that
        results are probabilistic without saying what produced them (AC 10).
        """
        return cls(
            text=DEFAULT_DISCLAIMER_TEXT,
            model_reference=model_reference,
            prompt_version=prompt_version,
        )

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("the simulation disclaimer requires text")
        if not self.model_reference.strip():
            raise ValueError("the disclaimer must name the model that generated the brief")
        if not self.prompt_version.strip():
            raise ValueError("the disclaimer must name the prompt version that generated the brief")


@dataclass(frozen=True, slots=True)
class ActorSummary:
    """Institution, goals, constraints and adopted positions shown in section 2."""

    institution: str
    goals: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    adopted_positions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.institution.strip():
            raise ValueError("an actor summary requires an institution")


@dataclass(frozen=True, slots=True)
class PositionStance:
    """One recorded stance in a change visualisation."""

    round_no: int
    stance: str
    rationale: str | None = None

    def __post_init__(self) -> None:
        if self.round_no < 1:
            raise ValueError("negotiation rounds are 1-based")
        if not self.stance.strip():
            raise ValueError("a position stance requires a stance")


@dataclass(frozen=True, slots=True)
class PositionTimeline:
    """Stance trajectory across rounds for one actor."""

    actor: str
    stances: tuple[PositionStance, ...] = ()

    def __post_init__(self) -> None:
        if not self.actor.strip():
            raise ValueError("a position timeline requires an actor")


@dataclass(frozen=True, slots=True)
class BriefComponentSlot:
    """Ordinal and completion state of one mandated component."""

    kind: SectionKind
    ordinal: int
    completed: bool = False

    def __post_init__(self) -> None:
        if self.ordinal != SECTION_ORDINAL[self.kind]:
            raise ValueError(
                f"section {self.kind.value!r} belongs at ordinal {SECTION_ORDINAL[self.kind]}, "
                f"not {self.ordinal}"
            )


@dataclass(frozen=True, slots=True)
class TopicOutcome:
    """How one topic is stated: recommendation, blocked or still disputed (invariant 8)."""

    topic: str
    kind: OutcomeKind
    blocking_stakeholders: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.topic.strip():
            raise ValueError("a topic outcome requires a topic")
        if self.kind is OutcomeKind.BLOCKED and not self.blocking_stakeholders:
            raise ValueError("a blocked topic must name who blocked it")

    @property
    def is_recommendation(self) -> bool:
        """Whether this outcome may be rendered as agreed advice (never a blocked topic)."""
        return self.kind is OutcomeKind.RECOMMENDATION
