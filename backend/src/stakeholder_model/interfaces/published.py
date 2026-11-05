"""Published partner contract of StakeholderModel for other contexts (ADR-003, ACL).

Canonical: .pi/architecture/modules/stakeholder-model.md

NegotiationSession receives :class:`StakeholderProfileView`; GovernanceCompliance receives the
institutions-only allowlist. These views contain no repository, ORM, session or table type.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from evidence_corpus.domain.values import AuthorityTier
from stakeholder_model.application.dto import StakeholderProfileResult
from stakeholder_model.domain.agent_binding import AgentBinding
from stakeholder_model.domain.values import (
    AttributionStrength,
    BudgetPeriod,
    InstitutionCategory,
    InstitutionIdentity,
    PowerSourceKind,
    ProposalClass,
)


@dataclass(frozen=True, slots=True)
class InstitutionView:
    """Institutional identity as published to downstream contexts."""

    name: str
    short_name: str
    category: InstitutionCategory
    code: str


@dataclass(frozen=True, slots=True)
class InterestView:
    """A weighted goal scoped to a policy topic."""

    topic: str
    goal: str
    weight: float


@dataclass(frozen=True, slots=True)
class ConstraintView:
    """A hard limit the institution cannot concede."""

    statement: str
    topic: str


@dataclass(frozen=True, slots=True)
class BudgetView:
    """Spending envelope with its grounding citation."""

    amount_eur: Decimal
    period: BudgetPeriod
    tolerance: float
    source_citation: str
    source_kind: PowerSourceKind
    source_as_of: date


@dataclass(frozen=True, slots=True)
class MandateScopeView:
    """Admissible range of agreement and its grounding citation."""

    topics: tuple[str, ...]
    description: str
    source_citation: str
    source_kind: PowerSourceKind
    source_as_of: date


@dataclass(frozen=True, slots=True)
class PriorityView:
    """Ordered policy priority."""

    rank: int
    topic: str


@dataclass(frozen=True, slots=True)
class VetoRightView:
    """A blocking competence over a proposal class, never over one proposal id."""

    proposal_class: ProposalClass
    source_citation: str
    source_kind: PowerSourceKind
    source_as_of: date


@dataclass(frozen=True, slots=True)
class PositionView:
    """Provenance-backed position reference published to NegotiationSession."""

    position_id: str
    stance: str
    attribution: AttributionStrength
    stated_on: date
    usable: bool
    passage_id: str


@dataclass(frozen=True, slots=True)
class StakeholderProfileView:
    """Complete partner contract: mandate, interests, constraints, red lines and positions."""

    stakeholder_id: str
    identity: InstitutionView
    interests: tuple[InterestView, ...]
    constraints: tuple[ConstraintView, ...]
    budget: BudgetView
    mandate_scope: MandateScopeView
    priorities: tuple[PriorityView, ...]
    red_lines: tuple[str, ...]
    veto_rights: tuple[VetoRightView, ...]
    positions: tuple[PositionView, ...]
    profile_version: str


@dataclass(frozen=True, slots=True)
class AgentBindingView:
    """Immutable binding published for run invocation recording."""

    binding_id: str
    run_id: str
    stakeholder_id: str
    persona_version: str
    allowed_evidence_tiers: tuple[AuthorityTier, ...]
    red_lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InstitutionalAllowlistView:
    """The canonical institutions-only allowlist published to GovernanceCompliance."""

    institutions: tuple[InstitutionView, ...]


def to_profile_view(payload: object) -> StakeholderProfileView:
    """Map a profile result to the partner contract."""
    if not isinstance(payload, StakeholderProfileResult):
        raise TypeError("to_profile_view expects a StakeholderProfileResult")
    profile = payload.profile
    budget = profile.budget
    mandate = profile.mandate_scope
    return StakeholderProfileView(
        stakeholder_id=payload.stakeholder_id,
        identity=InstitutionView(
            name=payload.identity.name,
            short_name=payload.identity.short_name,
            category=payload.identity.category,
            code=payload.identity.code,
        ),
        interests=tuple(
            InterestView(topic=item.topic, goal=item.goal, weight=item.weight)
            for item in profile.interests
        ),
        constraints=tuple(
            ConstraintView(statement=item.statement, topic=item.topic)
            for item in profile.constraints
        ),
        budget=BudgetView(
            amount_eur=budget.amount_eur,
            period=budget.period,
            tolerance=budget.tolerance,
            source_citation=budget.source.citation,
            source_kind=budget.source.kind,
            source_as_of=budget.source.as_of,
        ),
        mandate_scope=MandateScopeView(
            topics=tuple(sorted(mandate.topics)),
            description=mandate.description,
            source_citation=mandate.source.citation,
            source_kind=mandate.source.kind,
            source_as_of=mandate.source.as_of,
        ),
        priorities=tuple(
            PriorityView(rank=item.rank, topic=item.topic) for item in profile.priorities
        ),
        red_lines=tuple(profile.red_lines),
        veto_rights=tuple(
            VetoRightView(
                proposal_class=item.proposal_class,
                source_citation=item.source.citation,
                source_kind=item.source.kind,
                source_as_of=item.source.as_of,
            )
            for item in payload.veto_rights
        ),
        positions=tuple(
            PositionView(
                position_id=position.id,
                stance=position.stance,
                attribution=position.attribution,
                stated_on=position.stated_on,
                usable=position.usable,
                passage_id=position.passage_id,
            )
            for position in payload.positions
        ),
        profile_version=profile.version,
    )


def to_binding_view(payload: object) -> AgentBindingView:
    """Map an AgentBinding to its published view."""
    if not isinstance(payload, AgentBinding):
        raise TypeError("to_binding_view expects an AgentBinding")
    return AgentBindingView(
        binding_id=payload.id,
        run_id=payload.run_id,
        stakeholder_id=payload.stakeholder_id,
        persona_version=payload.persona_version,
        allowed_evidence_tiers=tuple(
            sorted(payload.allowed_evidence_tiers, key=lambda tier: tier.value)
        ),
        red_lines=payload.red_lines,
    )


def to_allowlist_view(institutions: object) -> InstitutionalAllowlistView:
    """Map registered identities to the institutions-only allowlist."""
    if not isinstance(institutions, (list, tuple)):
        raise TypeError("to_allowlist_view expects a sequence of InstitutionIdentity")
    identities = list(institutions)
    if not all(isinstance(identity, InstitutionIdentity) for identity in identities):
        raise TypeError("to_allowlist_view expects InstitutionIdentity values")
    return InstitutionalAllowlistView(
        institutions=tuple(
            InstitutionView(
                name=identity.name,
                short_name=identity.short_name,
                category=identity.category,
                code=identity.code,
            )
            for identity in identities
        )
    )
