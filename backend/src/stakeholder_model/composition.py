"""Composition root of StakeholderModel (ADR-001, ADR-009).

Canonical: .pi/architecture/modules/stakeholder-model.md

The container loads and validates all nine personas at boot, seeds the in-memory registry, and
publishes the institutional allowlist to the downstream guard. A malformed persona aborts the
construction before the process starts serving.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from evidence_corpus.domain.published import PassageView
from shared.clock import SystemClock
from shared.config import Settings
from shared.db import Database, UnitOfWork
from shared.enums import Persistence
from shared.log_setup import get_logger
from stakeholder_model.application.ports import UnitOfWork as UnitOfWorkPort
from stakeholder_model.application.services import (
    BindAgentPersona,
    CitePowerSource,
    GetStakeholderProfile,
    ListHistoricalPositions,
    ListStakeholders,
    LoadPersonaCards,
    PublishInstitutionalAllowlist,
    RecordHistoricalPosition,
    RegisterStakeholder,
    SelectRelevantStakeholders,
    UpdateStakeholderProfile,
)
from stakeholder_model.domain.repositories import StakeholderRepository
from stakeholder_model.domain.services import CorpusAttributionRule, WeightedInterestScorer
from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import InstitutionIdentity
from stakeholder_model.infrastructure.guard import InstitutionalAllowlistGuard
from stakeholder_model.infrastructure.personas import PersonaFactory
from stakeholder_model.infrastructure.repository.memory import (
    InMemoryAgentBindingRepository,
    InMemoryStakeholderRepository,
)
from stakeholder_model.interfaces.published import (
    InstitutionalAllowlistView,
    to_allowlist_view,
)

logger = get_logger(__name__)


class CorpusPort(Protocol):
    """Narrow corpus capability needed by historical-position recording."""

    async def passages_about(self, identity: InstitutionIdentity) -> list[PassageView]: ...


class EmptyCorpusEvidence:
    """No-op corpus port until the extraction pipeline publishes institution queries."""

    async def passages_about(self, identity: InstitutionIdentity) -> list[PassageView]:
        return []


class _NullUnitOfWork:
    """Transaction scope for the in-memory family."""

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        yield None


@dataclass(frozen=True, slots=True)
class StakeholderModelContainer:
    """Ports and services the API shell reads from ``app.state.stakeholder_model``."""

    repository: StakeholderRepository
    bindings: InMemoryAgentBindingRepository
    guard: InstitutionalAllowlistGuard
    personas: tuple[Stakeholder, ...]
    allowlist: InstitutionalAllowlistView
    register_stakeholder: RegisterStakeholder
    update_profile: UpdateStakeholderProfile
    cite_power_source: CitePowerSource
    record_position: RecordHistoricalPosition
    select_stakeholders: SelectRelevantStakeholders
    bind_persona: BindAgentPersona
    get_profile: GetStakeholderProfile
    list_stakeholders: ListStakeholders
    list_positions: ListHistoricalPositions
    load_personas: LoadPersonaCards
    publish_allowlist: PublishInstitutionalAllowlist
    transaction: UnitOfWorkPort


def build_container(
    settings: Settings,
    database: Database | None = None,
    *,
    persona_directory: Path | None = None,
) -> StakeholderModelContainer:
    """Load personas, publish the allowlist and construct every application service."""
    loader = PersonaFactory(persona_directory)
    personas = tuple(loader.load_all())
    identities = tuple(persona.identity for persona in personas)
    logger.info(
        "stakeholder_personas_loaded",
        count=len(personas),
        codes=sorted(identity.code for identity in identities),
    )
    if settings.persistence is Persistence.POSTGRES:
        logger.warning(
            "stakeholder_profiles_in_memory",
            detail="durable profile adapter is a follow-up; runtime state resets on restart",
        )
    guard = InstitutionalAllowlistGuard(identities)
    repository = InMemoryStakeholderRepository(list(personas))
    bindings = InMemoryAgentBindingRepository()
    clock = SystemClock()
    unit_of_work: UnitOfWorkPort
    if settings.persistence is Persistence.POSTGRES and database is not None:
        unit_of_work = UnitOfWork(database.session_factory)
    else:
        unit_of_work = _NullUnitOfWork()

    return StakeholderModelContainer(
        repository=repository,
        bindings=bindings,
        guard=guard,
        personas=personas,
        allowlist=to_allowlist_view(identities),
        register_stakeholder=RegisterStakeholder(
            repository=repository,
            unit_of_work=unit_of_work,
            clock=clock,
        ),
        update_profile=UpdateStakeholderProfile(
            repository=repository,
            unit_of_work=unit_of_work,
            clock=clock,
        ),
        cite_power_source=CitePowerSource(
            repository=repository,
            unit_of_work=unit_of_work,
        ),
        record_position=RecordHistoricalPosition(
            repository=repository,
            corpus=EmptyCorpusEvidence(),
            attribution_rule=CorpusAttributionRule(),
            unit_of_work=unit_of_work,
            clock=clock,
        ),
        select_stakeholders=SelectRelevantStakeholders(
            repository=repository,
            scorer=WeightedInterestScorer(),
        ),
        bind_persona=BindAgentPersona(
            repository=repository,
            binding_repository=bindings,
            guard=guard,
            unit_of_work=unit_of_work,
            clock=clock,
        ),
        get_profile=GetStakeholderProfile(repository=repository),
        list_stakeholders=ListStakeholders(repository=repository),
        list_positions=ListHistoricalPositions(repository=repository),
        load_personas=LoadPersonaCards(loader=loader),
        publish_allowlist=PublishInstitutionalAllowlist(
            repository=repository,
            guard=guard,
        ),
        transaction=unit_of_work,
    )
