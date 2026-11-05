"""Stakeholder aggregate, profile and the person-representation invariant (ADR-008).

Canonical: .pi/architecture/modules/stakeholder-model.md

CONTRACT FREEZE — aggregate roots, field sets and command signatures are frozen. The invariant
guards are completed by the person/incomplete-profile/authority issues; no setter may bypass them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from stakeholder_model.domain.events import (
    AuthorityClaimRejected,
    DomainEvent,
    HistoricalPositionRecorded,
    MandateSourceCited,
    WeakAttributionFlagged,
)
from stakeholder_model.domain.values import (
    AttributionStrength,
    BudgetLimit,
    Constraint,
    DecisionPriority,
    Dependency,
    HistoricalPosition,
    InstitutionIdentity,
    Interest,
    MandateScope,
    MandateSource,
    NegotiatingPower,
    PassageId,
    ProfileVersion,
    StakeholderId,
    VetoRight,
)


@dataclass(slots=True)
class StakeholderProfile:
    """Mandate, interests, constraints, budget and priorities of one institution."""

    mandate_scope: MandateScope
    budget: BudgetLimit
    interests: list[Interest] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    priorities: list[DecisionPriority] = field(default_factory=list)
    red_lines: list[str] = field(default_factory=list)
    version: ProfileVersion = field(default_factory=lambda: ProfileVersion("v1"))

    def is_complete(self) -> bool:
        """Return whether the profile has at least one interest and one constraint."""
        raise NotImplementedError("StakeholderProfile.is_complete is implemented by issue #107")

    def add_interest(self, interest: Interest) -> None:
        """Add an interest; implemented by issue #103."""
        raise NotImplementedError("StakeholderProfile.add_interest is implemented by issue #103")

    def declare_constraint(self, constraint: Constraint) -> None:
        """Declare a hard constraint; implemented by issue #103."""
        raise NotImplementedError("StakeholderProfile.declare_constraint is implemented by #103")

    def assert_within_mandate(self, proposed_value: str) -> None:
        """Refuse a concession outside the declared mandate scope (invariant 3)."""
        raise NotImplementedError("assert_within_mandate is implemented by issue #103")


@dataclass(slots=True)
class Stakeholder:
    """An institution in the Austrian healthcare system — never a natural person."""

    id: StakeholderId
    identity: InstitutionIdentity
    profile: StakeholderProfile
    veto_rights: list[VetoRight] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    history: list[HistoricalPosition] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Guard institutions-only; implemented by issue #106."""
        return None

    def register_interest(self, interest: Interest) -> None:
        """Register a goal; implemented by issue #103."""
        raise NotImplementedError("Stakeholder.register_interest is implemented by issue #103")

    def declare_constraint(self, constraint: Constraint) -> None:
        """Declare a hard limit; implemented by issue #103."""
        raise NotImplementedError("Stakeholder.declare_constraint is implemented by issue #103")

    def activate(self) -> None:
        """Activate the stakeholder once the profile is complete; implemented by issue #107."""
        raise NotImplementedError("Stakeholder.activate is implemented by issue #107")

    def cite_power_source(
        self,
        power: VetoRight | MandateScope | BudgetLimit,
        source: MandateSource,
    ) -> None:
        """Ground a power claim in a citable instrument; implemented by issue #108."""
        raise NotImplementedError("cite_power_source is implemented by issue #108")

    def record_historical_position(
        self,
        stance: str,
        attribution: AttributionStrength,
        stated_on: date,
        passage_id: PassageId,
    ) -> HistoricalPosition:
        """Record a past stance with attribution strength; implemented by issue #110."""
        raise NotImplementedError("record_historical_position is implemented by issue #110")

    def negotiating_power(self) -> NegotiatingPower:
        """Derive leverage from grounded inputs only; implemented by issue #109."""
        raise NotImplementedError("negotiating_power is implemented by issue #109")

    def drain_events(self) -> list[DomainEvent]:
        """Return and clear pending domain events for the outbox; implemented by wiring."""
        raise NotImplementedError("drain_events is implemented by the wiring issue")


__all__ = [
    "AuthorityClaimRejected",
    "HistoricalPositionRecorded",
    "MandateSourceCited",
    "Stakeholder",
    "StakeholderProfile",
    "WeakAttributionFlagged",
]
