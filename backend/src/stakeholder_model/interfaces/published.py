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
from stakeholder_model.domain.values import (
    AttributionStrength,
    BudgetPeriod,
    InstitutionCategory,
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
    """Map a profile result to the partner contract; implemented by issue #115."""
    raise NotImplementedError("to_profile_view is implemented by issue #115")


def to_binding_view(payload: object) -> AgentBindingView:
    """Map an AgentBinding to its published view; implemented by issue #115."""
    raise NotImplementedError("to_binding_view is implemented by issue #115")


def to_allowlist_view(institutions: object) -> InstitutionalAllowlistView:
    """Map registered identities to the allowlist; implemented by issue #115."""
    raise NotImplementedError("to_allowlist_view is implemented by issue #115")
