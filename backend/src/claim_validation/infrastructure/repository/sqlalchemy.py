"""PostgreSQL adapters for ClaimValidation (issue #179)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from claim_validation.domain.claim import Claim
from claim_validation.domain.entities import ClaimVerification, ContradictionFinding, ExpertReview
from claim_validation.domain.values import (
    ClaimId,
    ClaimType,
    ContradictionId,
    MeasureReference,
    ReferenceFigure,
    ReferenceFigureId,
    ReviewId,
    VerificationPath,
    VerificationVerdict,
)
from claim_validation.infrastructure.repository.models import (
    ClaimRow,
    ContradictionRow,
    ReferenceFigureRow,
)
from evidence_corpus.domain.values import AuthorityTier


def measure_key(measure: MeasureReference) -> str:
    return "|".join((measure.measure, measure.unit, measure.period, measure.geography))


def _measure_payload(measure: MeasureReference) -> dict[str, str]:
    return {
        "measure": measure.measure,
        "unit": measure.unit,
        "period": measure.period,
        "geography": measure.geography,
    }


def _measure_from(payload: dict[str, str]) -> MeasureReference:
    return MeasureReference(
        payload["measure"], payload["unit"], payload["period"], payload["geography"]
    )


def _verification_payload(verification: ClaimVerification | None) -> dict[str, Any] | None:
    if verification is None:
        return None
    return {
        "verdict": verification.verdict.value,
        "path": verification.path.value,
        "sources": list(verification.sources),
        "method": verification.method,
        "reference_id": verification.reference_id,
        "asserted_value": str(verification.asserted_value)
        if verification.asserted_value is not None
        else None,
        "reference_value": str(verification.reference_value)
        if verification.reference_value is not None
        else None,
        "delta": str(verification.delta) if verification.delta is not None else None,
    }


def _verification_from(payload: dict[str, Any] | None) -> ClaimVerification | None:
    if payload is None:
        return None
    return ClaimVerification(
        verdict=VerificationVerdict(payload["verdict"]),
        path=VerificationPath(payload["path"]),
        sources=tuple(payload["sources"]),
        method=payload["method"],
        reference_id=ReferenceFigureId(payload["reference_id"])
        if payload["reference_id"] is not None
        else None,
        asserted_value=Decimal(payload["asserted_value"])
        if payload["asserted_value"] is not None
        else None,
        reference_value=Decimal(payload["reference_value"])
        if payload["reference_value"] is not None
        else None,
        delta=Decimal(payload["delta"]) if payload["delta"] is not None else None,
    )


def _review_payload(review: ExpertReview | None) -> dict[str, Any] | None:
    if review is None:
        return None
    return {
        "id": str(review.id),
        "question": review.question,
        "verdict": review.verdict.value,
        "basis": review.basis,
    }


def _review_from(payload: dict[str, Any] | None) -> ExpertReview | None:
    if payload is None:
        return None
    return ExpertReview(
        id=ReviewId(payload["id"]),
        question=payload["question"],
        verdict=VerificationVerdict(payload["verdict"]),
        basis=payload["basis"],
    )


class SqlAlchemyClaimRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, claim_id: ClaimId) -> Claim | None:
        async with self._session_factory() as session:
            row = await session.get(ClaimRow, str(claim_id))
        return _claim_from(row) if row is not None else None

    async def save(self, claim: Claim) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(ClaimRow, str(claim.id))
            if row is None:
                row = ClaimRow(id=str(claim.id))
                session.add(row)
            row.text = claim.text
            row.claim_type = claim.type.value
            row.measure_key = measure_key(claim.measure) if claim.measure is not None else None
            row.measure = _measure_payload(claim.measure) if claim.measure is not None else None
            row.verdict = claim.verdict.value
            row.verification = _verification_payload(claim.verification)
            row.review = _review_payload(claim.review)

    async def verified_for_measure(self, measure: MeasureReference) -> list[Claim]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ClaimRow).where(
                    ClaimRow.measure_key == measure_key(measure),
                    ClaimRow.verdict.in_(
                        [VerificationVerdict.VERIFIED.value, VerificationVerdict.CONTRADICTED.value]
                    ),
                )
            )
        return [_claim_from(row) for row in rows]

    async def all_claims(self) -> list[Claim]:
        async with self._session_factory() as session:
            rows = await session.scalars(select(ClaimRow).order_by(ClaimRow.updated_at))
        return [_claim_from(row) for row in rows]


class SqlAlchemyReferenceFigureRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def find(self, measure: MeasureReference) -> ReferenceFigure | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(ReferenceFigureRow).where(
                    ReferenceFigureRow.measure_key == measure_key(measure)
                )
            )
        return _figure_from(row) if row is not None else None

    async def register(self, figure: ReferenceFigure) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(ReferenceFigureRow, str(figure.id))
            if row is None:
                row = ReferenceFigureRow(id=str(figure.id))
                session.add(row)
            row.measure_key = measure_key(figure.measure)
            row.measure = _measure_payload(figure.measure)
            row.value = figure.value
            row.tier = figure.tier.value
            row.as_of = figure.as_of
            row.source_id = figure.source_id

    async def get(self, figure_id: ReferenceFigureId) -> ReferenceFigure | None:
        async with self._session_factory() as session:
            row = await session.get(ReferenceFigureRow, str(figure_id))
        return _figure_from(row) if row is not None else None

    async def list_all(self) -> list[ReferenceFigure]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ReferenceFigureRow).order_by(ReferenceFigureRow.created_at)
            )
        return [_figure_from(row) for row in rows]


class SqlAlchemyContradictionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, finding: ContradictionFinding) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(ContradictionRow, str(finding.id))
            if row is None:
                row = ContradictionRow(id=str(finding.id))
                session.add(row)
            row.claim_id_a = str(finding.claim_id_a)
            row.claim_id_b = str(finding.claim_id_b)
            row.measure = _measure_payload(finding.measure)
            row.delta = finding.delta

    async def list_for_claim(self, claim_id: ClaimId) -> list[ContradictionFinding]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ContradictionRow).where(
                    (ContradictionRow.claim_id_a == str(claim_id))
                    | (ContradictionRow.claim_id_b == str(claim_id))
                )
            )
        return [_finding_from(row) for row in rows]

    async def list_all(self) -> list[ContradictionFinding]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ContradictionRow).order_by(ContradictionRow.created_at)
            )
        return [_finding_from(row) for row in rows]


def _claim_from(row: ClaimRow) -> Claim:
    return Claim(
        id=ClaimId(row.id),
        text=row.text,
        type=ClaimType(row.claim_type),
        measure=_measure_from(row.measure) if row.measure is not None else None,
        verdict=VerificationVerdict(row.verdict),
        verification=_verification_from(row.verification),
        review=_review_from(row.review),
    )


def _figure_from(row: ReferenceFigureRow) -> ReferenceFigure:
    return ReferenceFigure(
        id=ReferenceFigureId(row.id),
        measure=_measure_from(row.measure),
        value=Decimal(row.value),
        tier=AuthorityTier(row.tier),
        as_of=row.as_of,
        source_id=row.source_id,
    )


def _finding_from(row: ContradictionRow) -> ContradictionFinding:
    return ContradictionFinding(
        id=ContradictionId(row.id),
        claim_id_a=ClaimId(row.claim_id_a),
        claim_id_b=ClaimId(row.claim_id_b),
        measure=_measure_from(row.measure),
        delta=Decimal(row.delta),
    )
