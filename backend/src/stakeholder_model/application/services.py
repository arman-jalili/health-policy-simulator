"""Frozen application services of StakeholderModel.

Canonical: .pi/architecture/modules/stakeholder-model.md

Constructors, service names and ``execute`` signatures are frozen; the behaviour is implemented
against the domain contract and wired by the wiring issue.
"""

from __future__ import annotations

from evidence_corpus.domain.values import AuthorityTier
from shared.ids import new_id
from shared.metrics import METRICS
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
    BindingResult,
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
from stakeholder_model.domain.agent_binding import AgentBinding
from stakeholder_model.domain.errors import (
    StakeholderNotFound,
    UnsourcedAuthority,
)
from stakeholder_model.domain.events import (
    AgentPersonaBound,
)
from stakeholder_model.domain.repositories import (
    AgentBindingRepository,
    CorpusEvidencePort,
    StakeholderRepository,
)
from stakeholder_model.domain.services import AttributionRule, MaterialityScorer
from stakeholder_model.domain.stakeholder import Stakeholder, StakeholderProfile
from stakeholder_model.domain.values import (
    BindingId,
    PersonaVersion,
    ProfileVersion,
    ProposalClass,
    StakeholderId,
    VetoRight,
)


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
        """Register the institution and persist its complete profile."""
        stakeholder = Stakeholder(
            id=StakeholderId(f"stk_{request.identity.code}"),
            identity=request.identity,
            profile=StakeholderProfile(
                mandate_scope=request.mandate_scope,
                budget=request.budget,
                interests=list(request.interests),
                constraints=list(request.constraints),
                priorities=list(request.priorities),
                red_lines=[],
            ),
            veto_rights=list(request.veto_rights),
        )
        async with self._unit_of_work.transaction():
            await self._repository.save(stakeholder)
        METRICS.increment("stakeholder_registrations_total")
        return RegisterStakeholderResult(
            stakeholder_id=stakeholder.id,
            profile_version=stakeholder.profile.version,
        )


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
        """Update profile content for future runs without mutating active bindings."""
        stakeholder = await self._repository.get(request.stakeholder_id)
        if stakeholder is None:
            raise StakeholderNotFound(request.stakeholder_id)
        changed: list[str] = []
        if request.interests is not None:
            stakeholder.profile.interests = list(request.interests)
            changed.append("interests")
        if request.constraints is not None:
            stakeholder.profile.constraints = list(request.constraints)
            changed.append("constraints")
        if request.priorities is not None:
            stakeholder.profile.priorities = list(request.priorities)
            changed.append("priorities")
        if request.red_lines is not None:
            stakeholder.profile.red_lines = list(request.red_lines)
            changed.append("red_lines")
        stakeholder.profile.version = ProfileVersion(
            f"v-{self._clock.now().isoformat(timespec='microseconds')}"
        )
        async with self._unit_of_work.transaction():
            await self._repository.save(stakeholder)
        return UpdateProfileResult(
            stakeholder_id=stakeholder.id,
            profile_version=stakeholder.profile.version,
            changed_fields=tuple(changed),
        )


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
        """Cite a grounded power or return an explicit refusal for an unsourced claim."""
        stakeholder = await self._repository.get(request.stakeholder_id)
        if stakeholder is None:
            raise StakeholderNotFound(request.stakeholder_id)
        try:
            if request.proposal_class is not None:
                veto = VetoRight(
                    proposal_class=ProposalClass(request.proposal_class),
                    source=request.source,
                )
                stakeholder.cite_power_source(veto, request.source)
                stakeholder.veto_rights.append(veto)
            else:
                stakeholder.cite_power_source(
                    stakeholder.profile.mandate_scope,
                    request.source,
                )
        except UnsourcedAuthority as error:
            async with self._unit_of_work.transaction():
                await self._repository.save(stakeholder)
            METRICS.increment("stakeholder_authority_rejections_total")
            return CitePowerSourceResult(
                stakeholder_id=stakeholder.id,
                accepted=False,
                reason=error.message,
            )
        async with self._unit_of_work.transaction():
            await self._repository.save(stakeholder)
        return CitePowerSourceResult(stakeholder_id=stakeholder.id, accepted=True)


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
        """Record one attributed position and persist the aggregate."""
        stakeholder = await self._repository.get(request.stakeholder_id)
        if stakeholder is None:
            raise StakeholderNotFound(request.stakeholder_id)
        position = stakeholder.record_historical_position(
            stance=request.stance,
            attribution=request.attribution,
            stated_on=request.stated_on,
            passage_id=request.passage_id,
        )
        async with self._unit_of_work.transaction():
            await self._repository.save(stakeholder)
        METRICS.increment("stakeholder_positions_total")
        return HistoricalPositionResult(
            position_id=position.id,
            stakeholder_id=stakeholder.id,
            stance=position.stance,
            attribution=position.attribution,
            stated_on=position.stated_on,
            passage_id=position.passage_id,
            usable=position.usable,
        )


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
        METRICS.increment("stakeholder_selections_total")
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
        """Bind complete, institutions-only profiles to immutable personas."""
        bindings: list[BindingResult] = []
        async with self._unit_of_work.transaction():
            for stakeholder_id in request.stakeholder_ids:
                stakeholder = await self._repository.get(stakeholder_id)
                if stakeholder is None:
                    raise StakeholderNotFound(stakeholder_id)
                stakeholder.activate()
                await self._guard.assert_institution_only(stakeholder.identity)
                existing = await self._binding_repository.get_for_run(
                    request.run_id, stakeholder_id
                )
                binding = existing
                if binding is None:
                    binding = AgentBinding(
                        id=BindingId(new_id("bnd")),
                        run_id=request.run_id,
                        stakeholder_id=stakeholder_id,
                        persona_version=PersonaVersion(stakeholder.profile.version),
                        allowed_evidence_tiers=frozenset(AuthorityTier),
                        red_lines=tuple(stakeholder.profile.red_lines),
                    )
                    stakeholder.events.append(
                        AgentPersonaBound(
                            binding_id=binding.id,
                            run_id=request.run_id,
                            stakeholder_id=stakeholder_id,
                            persona_version=binding.persona_version,
                        )
                    )
                    await self._repository.save(stakeholder)
                    await self._binding_repository.save(binding)
                bindings.append(
                    BindingResult(
                        binding_id=binding.id,
                        stakeholder_id=stakeholder_id,
                        persona_version=binding.persona_version,
                    )
                )
        METRICS.increment("stakeholder_bindings_total", amount=float(len(bindings)))
        return BindPersonasResult(run_id=request.run_id, bindings=tuple(bindings))


class GetStakeholderProfile:
    """Read one institution with its profile, vetoes and derived power."""

    def __init__(self, *, repository: StakeholderRepository) -> None:
        self._repository = repository

    async def execute(self, request: GetStakeholderRequest) -> StakeholderProfileResult:
        """Read the profile with vetos, positions and derived power."""
        stakeholder = await self._repository.get(request.stakeholder_id)
        if stakeholder is None:
            raise StakeholderNotFound(request.stakeholder_id)
        return StakeholderProfileResult(
            stakeholder_id=stakeholder.id,
            identity=stakeholder.identity,
            profile=stakeholder.profile,
            veto_rights=tuple(stakeholder.veto_rights),
            power=stakeholder.negotiating_power(),
            positions=tuple(stakeholder.history),
        )


class ListStakeholders:
    """List the registry with profile summaries."""

    def __init__(self, *, repository: StakeholderRepository) -> None:
        self._repository = repository

    async def execute(self, request: ListStakeholdersRequest) -> list[StakeholderSummaryResult]:
        """List institutions, optionally filtered by category."""
        stakeholders = await self._repository.all_registered()
        return [
            StakeholderSummaryResult(
                stakeholder_id=stakeholder.id,
                identity=stakeholder.identity,
                interest_count=len(stakeholder.profile.interests),
                constraint_count=len(stakeholder.profile.constraints),
                profile_version=stakeholder.profile.version,
            )
            for stakeholder in stakeholders
            if request.category is None or stakeholder.identity.category is request.category
        ]


class ListHistoricalPositions:
    """Read a stakeholder's attributed history, optionally usable-only."""

    def __init__(self, *, repository: StakeholderRepository) -> None:
        self._repository = repository

    async def execute(self, request: ListHistoricalPositionsRequest) -> HistoricalPositionsResult:
        """List attributed positions, optionally excluding weak attribution."""
        stakeholder = await self._repository.get(request.stakeholder_id)
        if stakeholder is None:
            raise StakeholderNotFound(request.stakeholder_id)
        positions = [
            HistoricalPositionResult(
                position_id=position.id,
                stakeholder_id=stakeholder.id,
                stance=position.stance,
                attribution=position.attribution,
                stated_on=position.stated_on,
                passage_id=position.passage_id,
                usable=position.usable,
            )
            for position in stakeholder.history
            if not request.usable_only or position.usable
        ]
        return HistoricalPositionsResult(
            stakeholder_id=stakeholder.id,
            positions=tuple(positions),
        )


class LoadPersonaCards:
    """Load and validate all persona cards at boot; an invalid card aborts startup."""

    def __init__(self, *, loader: PersonaLoaderPort) -> None:
        self._loader = loader

    async def execute(self) -> tuple[PersonaCardResult, ...]:
        """Load and validate all persona cards."""
        cards = []
        for stakeholder in self._loader.load_all():
            stakeholder.activate()
            cards.append(
                PersonaCardResult(
                    code=stakeholder.identity.code,
                    identity=stakeholder.identity,
                    interest_count=len(stakeholder.profile.interests),
                    constraint_count=len(stakeholder.profile.constraints),
                    persona_version=PersonaVersion(stakeholder.profile.version),
                )
            )
        return tuple(cards)


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
        """Publish registered institutional identities to the downstream guard."""
        stakeholders = await self._repository.all_registered()
        identities = tuple(stakeholder.identity for stakeholder in stakeholders)
        await self._guard.publish_allowlist(identities)
        METRICS.increment("stakeholder_allowlist_publishes_total")
        return InstitutionalAllowlistResult(institutions=identities)
