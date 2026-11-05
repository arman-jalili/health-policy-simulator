"""Application-layer result DTOs of StakeholderModel.

Canonical: .pi/architecture/modules/stakeholder-model.md

Frozen interface: these are the shapes the HTTP layer and the ACL serialise. Framework-free; the
pydantic schemas in ``interfaces/http/schemas.py`` mirror them. Published views in
``interfaces/published.py`` deliberately expose no repository or ORM types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from stakeholder_model.domain.stakeholder import StakeholderProfile
from stakeholder_model.domain.values import (
    AttributionStrength,
    DecisionPriority,
    HistoricalPosition,
    InstitutionIdentity,
    MaterialityScore,
    NegotiatingPower,
    PassageId,
    PersonaVersion,
    ProfileVersion,
    StakeholderId,
    VetoRight,
)


@dataclass(frozen=True, slots=True)
class StakeholderSummaryResult:
    """Registry row: identity plus profile counts without the full profile."""

    stakeholder_id: StakeholderId
    identity: InstitutionIdentity
    interest_count: int
    constraint_count: int
    profile_version: ProfileVersion


@dataclass(frozen=True, slots=True)
class StakeholderProfileResult:
    """One registered institution with its complete profile and derived power."""

    stakeholder_id: StakeholderId
    identity: InstitutionIdentity
    profile: StakeholderProfile
    veto_rights: tuple[VetoRight, ...]
    power: NegotiatingPower
    positions: tuple[HistoricalPosition, ...] = ()


@dataclass(frozen=True, slots=True)
class RegisterStakeholderResult:
    """Output of ``RegisterStakeholder``."""

    stakeholder_id: StakeholderId
    profile_version: ProfileVersion


@dataclass(frozen=True, slots=True)
class UpdateProfileResult:
    """Output of ``UpdateStakeholderProfile``; the new version applies to future runs."""

    stakeholder_id: StakeholderId
    profile_version: ProfileVersion
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CitePowerSourceResult:
    """Output of ``CitePowerSource``; refusals are data, not 5xx errors."""

    stakeholder_id: StakeholderId
    accepted: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalPositionResult:
    """One attributed historical position as returned by the application layer."""

    position_id: str
    stakeholder_id: StakeholderId
    stance: str
    attribution: AttributionStrength
    stated_on: date
    passage_id: PassageId
    usable: bool


@dataclass(frozen=True, slots=True)
class HistoricalPositionsResult:
    """Output of ``ListHistoricalPositions``."""

    stakeholder_id: StakeholderId
    positions: tuple[HistoricalPositionResult, ...]


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """One institution selected for a moderator mandate, with its materiality."""

    stakeholder_id: StakeholderId
    materiality: MaterialityScore


@dataclass(frozen=True, slots=True)
class SelectStakeholdersResult:
    """Output of ``SelectRelevantStakeholders``, ordered by descending materiality."""

    run_id: str
    mandate: str
    selections: tuple[SelectionResult, ...]
    priorities: tuple[DecisionPriority, ...] = ()


@dataclass(frozen=True, slots=True)
class BindingResult:
    """One immutable agent binding."""

    binding_id: str
    stakeholder_id: StakeholderId
    persona_version: PersonaVersion


@dataclass(frozen=True, slots=True)
class BindPersonasResult:
    """Output of ``BindAgentPersona`` for all requested institutions."""

    run_id: str
    bindings: tuple[BindingResult, ...]


@dataclass(frozen=True, slots=True)
class PersonaCardResult:
    """A validated persona card loaded at boot, without exposing YAML internals."""

    code: str
    identity: InstitutionIdentity
    interest_count: int
    constraint_count: int
    persona_version: PersonaVersion


@dataclass(frozen=True, slots=True)
class InstitutionalAllowlistResult:
    """The institutional allowlist published to GovernanceCompliance."""

    institutions: tuple[InstitutionIdentity, ...]


@dataclass(frozen=True, slots=True)
class HistoricalPositionViewResult:
    """Alias-friendly result used by the partner contract mapper."""

    position: HistoricalPosition
