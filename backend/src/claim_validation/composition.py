"""Composition root of ClaimValidation (ADR-001, ADR-009; issue #178)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from claim_validation.application.services import (
    FlagUnsupportedAssertion,
    GetClaim,
    ListContradictions,
    ListReferenceFigures,
    RecordContradiction,
    RegisterReferenceFigure,
    ResolveExpertReview,
    VerifyClaim,
)
from claim_validation.domain.repositories import (
    ClaimRepository,
    ContradictionRepository,
    ReferenceFigureRepository,
)
from claim_validation.infrastructure.evidence import EmptyEvidence
from claim_validation.infrastructure.number_parser import GermanNumberParser
from claim_validation.infrastructure.repository.memory import (
    InMemoryClaimRepository,
    InMemoryContradictionRepository,
    InMemoryReferenceFigureRepository,
)
from claim_validation.infrastructure.repository.sqlalchemy import (
    SqlAlchemyClaimRepository,
    SqlAlchemyContradictionRepository,
    SqlAlchemyReferenceFigureRepository,
)
from shared.config import Settings
from shared.db import Database
from shared.enums import Persistence


@dataclass(frozen=True, slots=True)
class ClaimValidationContainer:
    claims: ClaimRepository
    references: ReferenceFigureRepository
    contradictions: ContradictionRepository
    verify_claim: VerifyClaim
    flag_unsupported: FlagUnsupportedAssertion
    get_claim: GetClaim
    register_reference_figure: RegisterReferenceFigure
    list_reference_figures: ListReferenceFigures
    list_contradictions: ListContradictions
    record_contradiction: RecordContradiction
    resolve_expert_review: ResolveExpertReview

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        yield None


def build_container(
    settings: Settings, database: Database | None = None
) -> ClaimValidationContainer:
    """Select durable PostgreSQL adapters unless memory is explicitly configured."""
    if settings.persistence is Persistence.POSTGRES:
        if database is None:
            raise ValueError(
                "PERSISTENCE=postgres requires a Database; the application shell owns the engine"
            )
        claims: ClaimRepository = SqlAlchemyClaimRepository(database.session_factory)
        references: ReferenceFigureRepository = SqlAlchemyReferenceFigureRepository(
            database.session_factory
        )
        contradictions: ContradictionRepository = SqlAlchemyContradictionRepository(
            database.session_factory
        )
    else:
        claims = InMemoryClaimRepository()
        references = InMemoryReferenceFigureRepository()
        contradictions = InMemoryContradictionRepository()
    parser = GermanNumberParser()
    evidence = EmptyEvidence()
    return ClaimValidationContainer(
        claims=claims,
        references=references,
        contradictions=contradictions,
        verify_claim=VerifyClaim(
            claims=claims,
            references=references,
            parser=parser,
            evidence=evidence,
        ),
        flag_unsupported=FlagUnsupportedAssertion(claims),
        get_claim=GetClaim(claims),
        register_reference_figure=RegisterReferenceFigure(references),
        list_reference_figures=ListReferenceFigures(references),
        list_contradictions=ListContradictions(contradictions),
        record_contradiction=RecordContradiction(contradictions),
        resolve_expert_review=ResolveExpertReview(claims),
    )
