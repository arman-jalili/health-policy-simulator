"""Frozen value objects and enums of the StakeholderModel bounded context.

Canonical: .pi/architecture/modules/stakeholder-model.md

CONTRACT FREEZE — names, field sets, enum members and constructor invariants below are the
published contract. Implementation issues add behaviour; renaming or removing a field is a
contract change, not a refactor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import NewType

StakeholderId = NewType("StakeholderId", str)
"""Identity of an institution in the registry (``stk_...``)."""

BindingId = NewType("BindingId", str)
"""Identity of one immutable AgentBinding (``bnd_...``)."""

PositionId = NewType("PositionId", str)
"""Identity of one historical position (``pos_...``)."""

RunId = NewType("RunId", str)
"""Simulation run the binding belongs to (``run_...``)."""

ProfileVersion = NewType("ProfileVersion", str)
"""Monotonic profile revision used by optimistic concurrency and audit."""

PersonaVersion = NewType("PersonaVersion", str)
"""Version of the persona configuration bound for a run."""

PassageId = NewType("PassageId", str)
"""EvidenceCorpus passage identity; the context stores references, never corpus rows."""


class InstitutionCategory(StrEnum):
    """Coarse institutional role in the Austrian healthcare system."""

    PAYER = "payer"
    PROVIDER = "provider"
    PROFESSIONAL_BODY = "professional_body"
    PATIENT_REPRESENTATION = "patient_representation"
    MINISTRY = "ministry"
    REGULATOR = "regulator"
    INSURER_ASSOCIATION = "insurer_association"
    HOSPITAL_OPERATOR = "hospital_operator"
    OTHER = "other"


class PowerSourceKind(StrEnum):
    """Admissible legal/institutional instrument grounding a power claim."""

    STATUTORY = "statutory"
    CONTRACTUAL = "contractual"
    REGULATORY = "regulatory"
    BUDGETARY = "budgetary"
    UNSPECIFIED = "unspecified"


class BudgetPeriod(StrEnum):
    """Period a budget ceiling applies to."""

    ANNUAL = "annual"
    BIENNIAL = "biennial"
    PER_RUN = "per_run"


class ProposalClass(StrEnum):
    """Class of proposal a veto can block; never an individual proposal id."""

    STATUTORY_BENEFIT_CHANGE = "statutory_benefit_change"
    BUDGET_FRAME = "budget_frame"
    SERVICE_CATALOGUE = "service_catalogue"
    FEE_SCHEDULE = "fee_schedule"
    HOSPITAL_PLAN = "hospital_plan"
    OTHER = "other"


class DependencyKind(StrEnum):
    """Directional relation between two institutions."""

    APPROVAL = "approval"
    FUNDING = "funding"
    INFORMATION = "information"
    SERVICE = "service"


class AttributionStrength(StrEnum):
    """How firmly a source attributes a position to an institution."""

    EXPLICIT = "explicit"
    REPORTED = "reported"
    MENTION = "mention"

    def is_explicit(self) -> bool:
        """Return whether the source is an explicit institutional statement."""
        return self is AttributionStrength.EXPLICIT

    @property
    def is_usable(self) -> bool:
        """Only explicit attribution may override a current persona position."""
        return self.is_explicit()


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


def _require_unit_interval(value: float, field_name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be within [0, 1]")


_PERSON_HONORIFICS = ("Dr.", "Mag.", "Prof.", "DI ", "HR ")


@dataclass(frozen=True, slots=True)
class InstitutionIdentity:
    """Canonical institutional identity — never a natural person."""

    name: str
    short_name: str
    category: InstitutionCategory
    code: str
    is_natural_person: bool = False

    def __post_init__(self) -> None:
        _require_text(self.name, "InstitutionIdentity.name")
        _require_text(self.short_name, "InstitutionIdentity.short_name")
        _require_text(self.code, "InstitutionIdentity.code")

    @property
    def is_person(self) -> bool:
        """Return whether the identity represents a natural person.

        The explicit flag is authoritative. An honorific prefix is also refused so a persona
        configuration cannot smuggle an individual in by omitting the flag.
        """
        return self.is_natural_person or self.name.strip().startswith(_PERSON_HONORIFICS)


@dataclass(frozen=True, slots=True)
class MandateSource:
    """Citable instrument grounding a mandate, budget or veto claim."""

    kind: PowerSourceKind
    citation: str
    as_of: date

    def __post_init__(self) -> None:
        _require_text(self.citation, "MandateSource.citation")


@dataclass(frozen=True, slots=True)
class MandateScope:
    """Admissible range of agreement; bounds every concession."""

    topics: frozenset[str]
    description: str
    source: MandateSource

    def __post_init__(self) -> None:
        if not self.topics:
            raise ValueError("MandateScope.topics must contain at least one topic")
        _require_text(self.description, "MandateScope.description")

    def covers(self, topic: str) -> bool:
        """Return whether ``topic`` lies inside the declared mandate scope."""
        normalised = topic.strip().casefold()
        return normalised in {declared.strip().casefold() for declared in self.topics}


@dataclass(frozen=True, slots=True)
class Interest:
    """Weighted goal scoped to policy topics."""

    topic: str
    goal: str
    weight: float

    def __post_init__(self) -> None:
        _require_text(self.topic, "Interest.topic")
        _require_text(self.goal, "Interest.goal")
        _require_unit_interval(self.weight, "Interest.weight")


@dataclass(frozen=True, slots=True)
class Constraint:
    """Hard limit the institution cannot concede."""

    statement: str
    topic: str

    def __post_init__(self) -> None:
        _require_text(self.statement, "Constraint.statement")
        _require_text(self.topic, "Constraint.topic")


@dataclass(frozen=True, slots=True)
class BudgetLimit:
    """Numeric spending envelope with its grounding instrument."""

    amount_eur: Decimal
    period: BudgetPeriod
    tolerance: float
    source: MandateSource

    def __post_init__(self) -> None:
        if self.amount_eur < 0:
            raise ValueError("BudgetLimit.amount_eur must be non-negative")
        _require_unit_interval(self.tolerance, "BudgetLimit.tolerance")

    def allows(self, amount_eur: Decimal) -> bool:
        """Return whether an amount fits the envelope including its declared tolerance."""
        if amount_eur < 0:
            raise ValueError("amount_eur must be non-negative")
        return amount_eur <= self.amount_eur * (Decimal("1") + Decimal(str(self.tolerance)))


@dataclass(frozen=True, slots=True)
class DecisionPriority:
    """Ordered ranking of policy topics."""

    rank: int
    topic: str

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("DecisionPriority.rank must be at least 1")
        _require_text(self.topic, "DecisionPriority.topic")


@dataclass(frozen=True, slots=True)
class VetoRight:
    """Power to block a proposal class outright — deliberately no proposal id field."""

    proposal_class: ProposalClass
    source: MandateSource


@dataclass(frozen=True, slots=True)
class Dependency:
    """Directional relation between two institutions."""

    from_id: StakeholderId
    to_id: StakeholderId
    kind: DependencyKind
    strength: float

    def __post_init__(self) -> None:
        if self.from_id == self.to_id:
            raise ValueError("Dependency must link two different institutions")
        _require_unit_interval(self.strength, "Dependency.strength")


@dataclass(frozen=True, slots=True)
class NegotiatingPower:
    """Derived leverage; recomputed from grounded inputs, never assigned."""

    scope: float
    budget: float
    vetoes: float
    centrality: float
    total: float

    def __post_init__(self) -> None:
        for name in ("scope", "budget", "vetoes", "centrality", "total"):
            _require_unit_interval(getattr(self, name), f"NegotiatingPower.{name}")

    @classmethod
    def derive(
        cls,
        *,
        mandate_scope: MandateScope,
        budget: BudgetLimit,
        veto_rights: list[VetoRight],
        dependencies: list[Dependency],
    ) -> NegotiatingPower:
        """Derive power from grounded inputs; implemented by issue #109."""
        raise NotImplementedError("NegotiatingPower.derive is implemented by issue #109")


@dataclass(frozen=True, slots=True)
class HistoricalPosition:
    """Provenance-backed past stance, weighted below current explicit statements."""

    id: PositionId
    stance: str
    attribution: AttributionStrength
    stated_on: date
    passage_id: PassageId
    usable: bool

    def __post_init__(self) -> None:
        _require_text(self.stance, "HistoricalPosition.stance")

    @classmethod
    def new(
        cls,
        *,
        stance: str,
        attribution: AttributionStrength,
        stated_on: date,
        passage_id: PassageId,
    ) -> HistoricalPosition:
        """Create a position whose usability is derived from attribution strength."""
        raise NotImplementedError("HistoricalPosition.new is implemented by issue #110")


@dataclass(frozen=True, slots=True)
class MaterialityScore:
    """Bounded materiality of an institution for one moderator mandate."""

    value: float

    def __post_init__(self) -> None:
        _require_unit_interval(self.value, "MaterialityScore.value")


@dataclass(frozen=True, slots=True)
class PersonaCard:
    """Validated persona configuration loaded from YAML (configuration, not aggregate state)."""

    code: str
    identity: InstitutionIdentity
    interests: tuple[Interest, ...] = field(default_factory=tuple)
    constraints: tuple[Constraint, ...] = field(default_factory=tuple)
    red_lines: tuple[str, ...] = field(default_factory=tuple)
    version: PersonaVersion = PersonaVersion("v1")

    def __post_init__(self) -> None:
        _require_text(self.code, "PersonaCard.code")
