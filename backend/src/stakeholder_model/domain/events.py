"""Frozen domain-event payloads of the StakeholderModel context (ADR-003, ADR-008).

Canonical: .pi/architecture/modules/stakeholder-model.md

Event names are past-tense immutable facts. Payloads carry ids plus the minimum a consumer needs;
consumers re-read the profile for detail. Persona prose and scoring arithmetic are not events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from stakeholder_model.domain.values import (
    AttributionStrength,
    Constraint,
    DependencyKind,
    InstitutionIdentity,
    MandateSource,
    NegotiatingPower,
    ProposalClass,
    RunId,
)


@dataclass(frozen=True, slots=True)
class StakeholderRegistered:
    """An institution entered the registry with a mandate and profile."""

    name: ClassVar[str] = "StakeholderRegistered"
    stakeholder_id: str
    identity: InstitutionIdentity
    interest_count: int
    constraint_count: int


@dataclass(frozen=True, slots=True)
class StakeholderProfileUpdated:
    """Interests, constraints or priorities changed; applies to future runs only."""

    name: ClassVar[str] = "StakeholderProfileUpdated"
    stakeholder_id: str
    changed_fields: tuple[str, ...]
    profile_version: str


@dataclass(frozen=True, slots=True)
class AgentPersonaBound:
    """An institution was bound to a persona for one run."""

    name: ClassVar[str] = "AgentPersonaBound"
    binding_id: str
    run_id: RunId
    stakeholder_id: str
    persona_version: str


@dataclass(frozen=True, slots=True)
class HistoricalPositionRecorded:
    """A past stance was extracted and stored with provenance."""

    name: ClassVar[str] = "HistoricalPositionRecorded"
    stakeholder_id: str
    position_id: str
    attribution: AttributionStrength
    passage_id: str


@dataclass(frozen=True, slots=True)
class MandateViolationDetected:
    """A proposed concession exceeded a declared constraint or budget."""

    name: ClassVar[str] = "MandateViolationDetected"
    stakeholder_id: str
    constraint: Constraint
    proposed_value: str


@dataclass(frozen=True, slots=True)
class MandateSourceCited:
    """An authority claim was grounded in a citable instrument."""

    name: ClassVar[str] = "MandateSourceCited"
    stakeholder_id: str
    power_type: str
    citation: str


@dataclass(frozen=True, slots=True)
class AuthorityClaimRejected:
    """A power was refused because it lacked an admissible source."""

    name: ClassVar[str] = "AuthorityClaimRejected"
    stakeholder_id: str
    power_type: str
    reason: str


@dataclass(frozen=True, slots=True)
class WeakAttributionFlagged:
    """History was stored with weak attribution, unusable for overriding."""

    name: ClassVar[str] = "WeakAttributionFlagged"
    stakeholder_id: str
    passage_id: str
    attribution: AttributionStrength


@dataclass(frozen=True, slots=True)
class NegotiatingPowerChanged:
    """Derived leverage changed, altering the viable coalitions."""

    name: ClassVar[str] = "NegotiatingPowerChanged"
    stakeholder_id: str
    previous: NegotiatingPower
    current: NegotiatingPower
    drivers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VetoRightRegistered:
    """A blocking competence over a proposal class was declared."""

    name: ClassVar[str] = "VetoRightRegistered"
    stakeholder_id: str
    proposal_class: ProposalClass
    mandate_source: MandateSource


@dataclass(frozen=True, slots=True)
class DependencyRecorded:
    """A directional dependency between two institutions was registered."""

    name: ClassVar[str] = "DependencyRecorded"
    from_id: str
    to_id: str
    kind: DependencyKind
    strength: float


type DomainEvent = (
    StakeholderRegistered
    | StakeholderProfileUpdated
    | AgentPersonaBound
    | HistoricalPositionRecorded
    | MandateViolationDetected
    | MandateSourceCited
    | AuthorityClaimRejected
    | WeakAttributionFlagged
    | NegotiatingPowerChanged
    | VetoRightRegistered
    | DependencyRecorded
)
