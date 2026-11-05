"""Stakeholder aggregate, profile and the person-representation invariant (ADR-008).

Canonical: .pi/architecture/modules/stakeholder-model.md

CONTRACT FREEZE — aggregate roots, field sets and command signatures are frozen. The invariant
guards are completed by the person/incomplete-profile/authority issues; no setter may bypass them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from stakeholder_model.domain.errors import (
    IncompleteProfile,
    PersonRepresentationForbidden,
    UnsourcedAuthority,
)
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
    PowerSourceKind,
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
        return bool(self.interests) and bool(self.constraints)

    def missing(self) -> tuple[str, ...]:
        """Return the required profile parts that are still absent."""
        missing: list[str] = []
        if not self.interests:
            missing.append("interests")
        if not self.constraints:
            missing.append("constraints")
        return tuple(missing)

    def add_interest(self, interest: Interest) -> None:
        """Add an interest to the profile."""
        self.interests.append(interest)

    def declare_constraint(self, constraint: Constraint) -> None:
        """Declare a hard constraint on the profile."""
        self.constraints.append(constraint)

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
        """Refuse any institution represented by a natural person (invariant 1)."""
        if self.identity.is_person:
            raise PersonRepresentationForbidden(self.identity.name)

    def register_interest(self, interest: Interest) -> None:
        """Register a weighted goal on the profile."""
        self.profile.add_interest(interest)

    def declare_constraint(self, constraint: Constraint) -> None:
        """Declare a hard limit on the profile."""
        self.profile.declare_constraint(constraint)

    def activate(self) -> None:
        """Activate the stakeholder once the profile is complete (invariant 2)."""
        missing = self.profile.missing()
        if missing:
            raise IncompleteProfile(self.id, missing)

    def cite_power_source(
        self,
        power: VetoRight | MandateScope | BudgetLimit,
        source: MandateSource | None,
    ) -> None:
        """Ground a power claim in a citable instrument (invariant 8)."""
        power_type = type(power).__name__
        if source is None or source.kind is PowerSourceKind.UNSPECIFIED:
            reason = "authority claim cites no admissible MandateSource"
            self.events.append(AuthorityClaimRejected(self.id, power_type, reason))
            raise UnsourcedAuthority(self.id, power_type)
        self.events.append(MandateSourceCited(self.id, power_type, source.citation))

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
        """Derive leverage from grounded inputs only; never assignable."""
        return NegotiatingPower.derive(
            mandate_scope=self.profile.mandate_scope,
            budget=self.profile.budget,
            veto_rights=self.veto_rights,
            dependencies=self.dependencies,
        )

    def drain_events(self) -> list[DomainEvent]:
        """Return and clear pending domain events for the outbox."""
        drained = list(self.events)
        self.events.clear()
        return drained


__all__ = [
    "AuthorityClaimRejected",
    "HistoricalPositionRecorded",
    "MandateSourceCited",
    "Stakeholder",
    "StakeholderProfile",
    "WeakAttributionFlagged",
]
