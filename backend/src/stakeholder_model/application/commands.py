"""Application-layer request DTOs (commands and queries) of StakeholderModel.

Canonical: .pi/architecture/modules/stakeholder-model.md

Frozen interface: one request object per use case, so adding a parameter never changes a service
signature callers already implement. Framework-free on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from stakeholder_model.domain.values import (
    AttributionStrength,
    BudgetLimit,
    Constraint,
    DecisionPriority,
    InstitutionCategory,
    InstitutionIdentity,
    Interest,
    MandateScope,
    MandateSource,
    PassageId,
    ProposalClass,
    RunId,
    StakeholderId,
    VetoRight,
)


@dataclass(frozen=True, slots=True)
class RegisterStakeholderRequest:
    """Register one institution with its complete mandate and profile."""

    identity: InstitutionIdentity
    mandate_scope: MandateScope
    budget: BudgetLimit
    interests: tuple[Interest, ...]
    constraints: tuple[Constraint, ...]
    priorities: tuple[DecisionPriority, ...] = ()
    veto_rights: tuple[VetoRight, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdateStakeholderProfileRequest:
    """Partially update a profile for future runs; the current version is immutable."""

    stakeholder_id: StakeholderId
    interests: tuple[Interest, ...] | None = None
    constraints: tuple[Constraint, ...] | None = None
    priorities: tuple[DecisionPriority, ...] | None = None
    red_lines: tuple[str, ...] | None = None
    expected_version: str | None = None


@dataclass(frozen=True, slots=True)
class CitePowerSourceRequest:
    """Ground a veto, mandate scope or budget limit in a citable instrument."""

    stakeholder_id: StakeholderId
    power_type: str
    source: MandateSource
    proposal_class: ProposalClass | None = None


@dataclass(frozen=True, slots=True)
class RecordHistoricalPositionRequest:
    """Record one attributed past stance extracted from the corpus."""

    stakeholder_id: StakeholderId
    stance: str
    attribution: AttributionStrength
    stated_on: date
    passage_id: PassageId


@dataclass(frozen=True, slots=True)
class ListHistoricalPositionsRequest:
    """Read a stakeholder's history, optionally excluding weak attribution."""

    stakeholder_id: StakeholderId
    usable_only: bool = False


@dataclass(frozen=True, slots=True)
class SelectRelevantStakeholdersRequest:
    """Select institutions material to one moderator mandate, with reasons."""

    run_id: RunId
    mandate: str


@dataclass(frozen=True, slots=True)
class BindAgentPersonaRequest:
    """Bind selected institutions to immutable personas for one run."""

    run_id: RunId
    stakeholder_ids: tuple[StakeholderId, ...]


@dataclass(frozen=True, slots=True)
class GetStakeholderRequest:
    """Read one registered institution and its profile."""

    stakeholder_id: StakeholderId


@dataclass(frozen=True, slots=True)
class ListStakeholdersRequest:
    """List registered institutions, optionally filtered by institutional category."""

    category: InstitutionCategory | None = None
