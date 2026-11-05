"""Frozen application services of StakeholderModel.

Canonical: .pi/architecture/modules/stakeholder-model.md

Constructors, service names and ``execute`` signatures are frozen; the behaviour is implemented
against the domain contract and wired by the wiring issue.
"""

from __future__ import annotations

from stakeholder_model.application.commands import (
    BindAgentPersonaRequest,
    CitePowerSourceRequest,
    GetStakeholderRequest,
    ListHistoricalPositionsRequest,
    ListStakeholdersRequest,
    RecordHistoricalPositionRequest,
    RegisterStakeholderRequest,
    SelectRelevantStakeholdersRequest,
    UpdateStakeholderProfileRequest,
)
from stakeholder_model.application.dto import (
    BindPersonasResult,
    CitePowerSourceResult,
    HistoricalPositionResult,
    HistoricalPositionsResult,
    InstitutionalAllowlistResult,
    PersonaCardResult,
    RegisterStakeholderResult,
    SelectionResult,
    SelectStakeholdersResult,
    StakeholderProfileResult,
    StakeholderSummaryResult,
    UpdateProfileResult,
)
from stakeholder_model.application.ports import (
    Clock,
    InstitutionalGuardPort,
    PersonaLoaderPort,
    UnitOfWork,
)
from stakeholder_model.domain.repositories import (
    AgentBindingRepository,
    CorpusEvidencePort,
    StakeholderRepository,
)
from stakeholder_model.domain.services import AttributionRule, MaterialityScorer


class RegisterStakeholder:
    """Transaction boundary: validate a complete profile and persist the institution."""

    def __init__(
        self,
        *,
        repository: StakeholderRepository,
        unit_of_work: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(self, request: RegisterStakeholderRequest) -> RegisterStakeholderResult:
        """Register the institution; implemented by issue #117."""
        raise NotImplementedError("RegisterStakeholder.execute is implemented by issue #117")


class UpdateStakeholderProfile:
    """Apply a profile revision for future runs without mutating an active binding."""

    def __init__(
        self,
        *,
        repository: StakeholderRepository,
        unit_of_work: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(self, request: UpdateStakeholderProfileRequest) -> UpdateProfileResult:
        """Update the profile; implemented by issue #117."""
        raise NotImplementedError("UpdateStakeholderProfile.execute is implemented by issue #117")


class CitePowerSource:
    """Ground an authority claim in a citable instrument or refuse it."""

    def __init__(
        self,
        *,
        repository: StakeholderRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._repository = repository
        self._unit_of_work = unit_of_work

    async def execute(self, request: CitePowerSourceRequest) -> CitePowerSourceResult:
        """Cite or refuse the power; implemented by issue #108."""
        raise NotImplementedError("CitePowerSource.execute is implemented by issue #108")


class RecordHistoricalPosition:
    """Fetch corpus passages, apply attribution rules and persist a position."""

    def __init__(
        self,
        *,
        repository: StakeholderRepository,
        corpus: CorpusEvidencePort,
        attribution_rule: AttributionRule,
        unit_of_work: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._corpus = corpus
        self._attribution_rule = attribution_rule
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(self, request: RecordHistoricalPositionRequest) -> HistoricalPositionResult:
        """Record the position; implemented by issue #110."""
        raise NotImplementedError("RecordHistoricalPosition.execute is implemented by issue #110")


class SelectRelevantStakeholders:
    """Score all registered institutions against a moderator mandate."""

    def __init__(
        self,
        *,
        repository: StakeholderRepository,
        scorer: MaterialityScorer,
    ) -> None:
        self._repository = repository
        self._scorer = scorer

    async def execute(self, request: SelectRelevantStakeholdersRequest) -> SelectStakeholdersResult:
        """Select registered institutions with non-zero materiality, best first."""
        stakeholders = await self._repository.all_registered()
        selections = [
            SelectionResult(
                stakeholder_id=stakeholder.id,
                materiality=self._scorer.score(stakeholder.profile, request.mandate),
            )
            for stakeholder in stakeholders
        ]
        material = sorted(
            (selection for selection in selections if selection.materiality.value > 0.0),
            key=lambda selection: (-selection.materiality.value, selection.stakeholder_id),
        )
        return SelectStakeholdersResult(
            run_id=request.run_id,
            mandate=request.mandate,
            selections=tuple(material),
        )


class BindAgentPersona:
    """Bind complete, institutions-only profiles to immutable agent personas."""

    def __init__(
        self,
        *,
        repository: StakeholderRepository,
        binding_repository: AgentBindingRepository,
        guard: InstitutionalGuardPort,
        unit_of_work: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._binding_repository = binding_repository
        self._guard = guard
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(self, request: BindAgentPersonaRequest) -> BindPersonasResult:
        """Bind personas; implemented by issue #117."""
        raise NotImplementedError("BindAgentPersona.execute is implemented by issue #117")


class GetStakeholderProfile:
    """Read one institution with its profile, vetoes and derived power."""

    def __init__(self, *, repository: StakeholderRepository) -> None:
        self._repository = repository

    async def execute(self, request: GetStakeholderRequest) -> StakeholderProfileResult:
        """Read the profile; implemented by issue #117."""
        raise NotImplementedError("GetStakeholderProfile.execute is implemented by issue #117")


class ListStakeholders:
    """List the registry with profile summaries."""

    def __init__(self, *, repository: StakeholderRepository) -> None:
        self._repository = repository

    async def execute(self, request: ListStakeholdersRequest) -> list[StakeholderSummaryResult]:
        """List institutions; implemented by issue #117."""
        raise NotImplementedError("ListStakeholders.execute is implemented by issue #117")


class ListHistoricalPositions:
    """Read a stakeholder's attributed history, optionally usable-only."""

    def __init__(self, *, repository: StakeholderRepository) -> None:
        self._repository = repository

    async def execute(self, request: ListHistoricalPositionsRequest) -> HistoricalPositionsResult:
        """List positions; implemented by issue #117."""
        raise NotImplementedError("ListHistoricalPositions.execute is implemented by issue #117")


class LoadPersonaCards:
    """Load and validate all persona cards at boot; an invalid card aborts startup."""

    def __init__(self, *, loader: PersonaLoaderPort) -> None:
        self._loader = loader

    async def execute(self) -> tuple[PersonaCardResult, ...]:
        """Load cards; implemented by issue #114."""
        raise NotImplementedError("LoadPersonaCards.execute is implemented by issue #114")


class PublishInstitutionalAllowlist:
    """Publish the canonical allowlist to GovernanceCompliance (ADR-007)."""

    def __init__(
        self,
        *,
        repository: StakeholderRepository,
        guard: InstitutionalGuardPort,
    ) -> None:
        self._repository = repository
        self._guard = guard

    async def execute(self) -> InstitutionalAllowlistResult:
        """Publish the allowlist; implemented by the wiring issue #117."""
        raise NotImplementedError("PublishInstitutionalAllowlist.execute is implemented by #117")
