"""Integration: claim validation survives a repository restart (issue #179)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from claim_validation.domain.claim import Claim
from claim_validation.domain.entities import ContradictionFinding
from claim_validation.domain.values import (
    ClaimId,
    ClaimType,
    ContradictionId,
    MeasureReference,
    ReferenceFigure,
    ReferenceFigureId,
    VerificationEvidence,
    VerificationPath,
    VerificationVerdict,
)
from claim_validation.infrastructure.repository.sqlalchemy import (
    SqlAlchemyClaimRepository,
    SqlAlchemyContradictionRepository,
    SqlAlchemyReferenceFigureRepository,
)
from evidence_corpus.domain.values import AuthorityTier
from shared.config import get_settings
from shared.ids import new_id

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("HPS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not DATABASE_URL,
        reason="DATABASE_URL is not set (start compose.yaml and export it)",
    ),
]


@pytest.fixture(scope="module")
def migrated() -> None:
    os.environ.setdefault("DATABASE_URL", DATABASE_URL or "")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    command.upgrade(config, "head")


@pytest.fixture
async def session_factory(
    migrated: None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(DATABASE_URL or "")
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def _measure(tag: str) -> MeasureReference:
    return MeasureReference(f"Kassenstellen {tag}", "count", "2026", "AT")


async def test_claim_and_reference_figure_round_trip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    measure = _measure(new_id("m"))
    reference = ReferenceFigure(
        id=ReferenceFigureId(new_id("fig")),
        measure=measure,
        value=Decimal("3.2"),
        tier=AuthorityTier.OFFICIAL_STATISTICS,
        as_of=date(2026, 1, 1),
        source_id="statistik_austria",
    )
    claims = SqlAlchemyClaimRepository(session_factory)
    references = SqlAlchemyReferenceFigureRepository(session_factory)
    await references.register(reference)

    claim = Claim(
        id=ClaimId(new_id("clm")),
        text="Es gibt 3,2 Mio Kassenstellen",
        type=ClaimType.QUANTITATIVE,
        measure=measure,
    )
    claim.verify(
        VerificationPath.QUANTITATIVE,
        VerificationEvidence(
            sources=(reference.source_id,),
            reference_figure=reference,
            asserted_value=Decimal("3.25"),
            asserted_measure=measure,
        ),
    )
    await claims.save(claim)
    claim.drain_events()

    restarted_claims = SqlAlchemyClaimRepository(session_factory)
    restarted_references = SqlAlchemyReferenceFigureRepository(session_factory)
    stored = await restarted_claims.get(claim.id)

    assert stored is not None
    assert stored.verdict is VerificationVerdict.VERIFIED
    assert stored.verification is not None
    assert stored.verification.delta == Decimal("0.05")
    assert (await restarted_references.find(measure)) == reference
    assert [item.id for item in await restarted_claims.verified_for_measure(measure)] == [claim.id]


async def test_contradiction_finding_round_trip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    measure = _measure(new_id("m"))
    finding = ContradictionFinding(
        id=ContradictionId(new_id("con")),
        claim_id_a=ClaimId(new_id("clm")),
        claim_id_b=ClaimId(new_id("clm")),
        measure=measure,
        delta=Decimal("0.9"),
    )
    contradictions = SqlAlchemyContradictionRepository(session_factory)
    await contradictions.save(finding)

    restarted = SqlAlchemyContradictionRepository(session_factory)
    assert [item.id for item in await restarted.list_all() if item.id == finding.id] == [finding.id]
    assert [item.id for item in await restarted.list_for_claim(finding.claim_id_a)] == [finding.id]


async def test_missing_reference_figure_is_absent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    references = SqlAlchemyReferenceFigureRepository(session_factory)
    assert await references.find(_measure(new_id("missing"))) is None
