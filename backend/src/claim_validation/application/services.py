"""Application services of ClaimValidation (issue #178)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from claim_validation.application.commands import (
    FlagUnsupportedAssertionRequest,
    GetClaimRequest,
    ListContradictionsRequest,
    ListReferenceFiguresRequest,
    RegisterReferenceFigureRequest,
    ResolveExpertReviewRequest,
    VerifyClaimRequest,
)
from claim_validation.application.dto import (
    ClaimDetailResult,
    ClaimVerdictResult,
    ContradictionResult,
    ReferenceFigureResult,
)
from claim_validation.application.ports import EvidencePort, NumberParserPort
from claim_validation.domain.claim import Claim
from claim_validation.domain.entities import ContradictionFinding
from claim_validation.domain.errors import ClaimNotFound, ReferenceMeasureMismatch
from claim_validation.domain.repositories import (
    ClaimRepository,
    ContradictionRepository,
    ReferenceFigureRepository,
)
from claim_validation.domain.services import path_for
from claim_validation.domain.values import (
    ClaimId,
    ClaimType,
    ReferenceFigure,
    ReferenceFigureId,
    VerificationEvidence,
)
from evidence_corpus.domain.values import AuthorityTier
from shared.errors import ValidationFailedError
from shared.ids import new_id
from shared.metrics import METRICS

_LEGAL_MARKERS = ("gesetz", "§", "verordnung", "asvg", "vertrag")
_CAUSAL_MARKERS = ("weil", "verursacht", "führt zu", "aufgrund", "bewirkt")


@dataclass(frozen=True, slots=True)
class VerifyClaim:
    claims: ClaimRepository
    references: ReferenceFigureRepository
    parser: NumberParserPort
    evidence: EvidencePort

    async def execute(self, request: VerifyClaimRequest) -> ClaimVerdictResult:
        claim_type = request.claim_type or _infer_claim_type(request)
        claim = Claim(
            id=ClaimId(new_id("clm")),
            text=request.text,
            type=claim_type,
            measure=request.measure,
        )
        evidence = await self._evidence_for(claim_type, request)
        claim.verify(path_for(claim_type), evidence)
        await self.claims.save(claim)
        claim.drain_events()
        METRICS.increment("claim_verifications_total", labels={"claim_type": claim_type.value})
        return _verdict_result(claim)

    async def _evidence_for(
        self, claim_type: ClaimType, request: VerifyClaimRequest
    ) -> VerificationEvidence:
        if claim_type is not ClaimType.QUANTITATIVE:
            return await self.evidence.evidence_for(claim_type, request.text)
        asserted = request.asserted_value
        if asserted is None:
            parsed = self.parser.parse(request.text)
            asserted = parsed[0] if parsed is not None else None
        measure = request.measure
        if measure is None:
            return VerificationEvidence(asserted_value=asserted)
        reference = await self.references.find(measure)
        if reference is not None and reference.measure != measure:
            raise ReferenceMeasureMismatch("reference figure measure does not match the claim")
        sources = (reference.source_id,) if reference is not None else ()
        return VerificationEvidence(
            sources=sources,
            reference_figure=reference,
            asserted_value=asserted,
            asserted_measure=measure,
        )


@dataclass(frozen=True, slots=True)
class FlagUnsupportedAssertion:
    claims: ClaimRepository

    async def execute(self, request: FlagUnsupportedAssertionRequest) -> ClaimVerdictResult:
        claim = await self._load(request.claim_id)
        claim.mark_unsupported(request.reason)
        await self.claims.save(claim)
        return _verdict_result(claim)

    async def _load(self, claim_id: ClaimId) -> Claim:
        claim = await self.claims.get(claim_id)
        if claim is None:
            raise ClaimNotFound(f"claim {claim_id} not found")
        return claim


@dataclass(frozen=True, slots=True)
class GetClaim:
    claims: ClaimRepository

    async def execute(self, request: GetClaimRequest) -> ClaimDetailResult:
        claim = await self.claims.get(request.claim_id)
        if claim is None:
            raise ClaimNotFound(f"claim {request.claim_id} not found")
        verification = claim.verification
        METRICS.increment("claim_reads_total")
        return ClaimDetailResult(
            claim_id=str(claim.id),
            text=claim.text,
            claim_type=claim.type,
            verdict=claim.verdict,
            path=verification.path if verification is not None else None,
            sources=verification.sources if verification is not None else (),
            review_verdict=claim.review.verdict if claim.review is not None else None,
            review_basis=claim.review.basis if claim.review is not None else None,
        )


@dataclass(frozen=True, slots=True)
class RegisterReferenceFigure:
    references: ReferenceFigureRepository

    async def execute(self, request: RegisterReferenceFigureRequest) -> ReferenceFigureResult:
        try:
            tier = AuthorityTier(request.tier)
        except ValueError as error:
            raise ValidationFailedError(f"unknown authority tier: {request.tier}") from error
        try:
            as_of = date.fromisoformat(request.as_of)
        except ValueError as error:
            raise ValidationFailedError(f"invalid as_of date: {request.as_of}") from error
        figure = ReferenceFigure(
            id=ReferenceFigureId(new_id("fig")),
            measure=request.measure,
            value=request.value,
            tier=tier,
            as_of=as_of,
            source_id=request.source_id,
        )
        await self.references.register(figure)
        METRICS.increment("reference_figures_registered_total")
        return _figure_result(figure)


@dataclass(frozen=True, slots=True)
class ListReferenceFigures:
    references: ReferenceFigureRepository

    async def execute(self, request: ListReferenceFiguresRequest) -> list[ReferenceFigureResult]:
        figures = await self.references.list_all()
        if request.measure is not None:
            figures = [figure for figure in figures if figure.measure == request.measure]
        return [_figure_result(figure) for figure in figures]


@dataclass(frozen=True, slots=True)
class ListContradictions:
    contradictions: ContradictionRepository

    async def execute(self, request: ListContradictionsRequest) -> list[ContradictionResult]:
        findings = await self.contradictions.list_all()
        return [
            ContradictionResult(
                finding_id=str(finding.id),
                claim_id_a=str(finding.claim_id_a),
                claim_id_b=str(finding.claim_id_b),
                measure=finding.measure.measure,
                delta=finding.delta,
            )
            for finding in findings
        ]


@dataclass(frozen=True, slots=True)
class RecordContradiction:
    contradictions: ContradictionRepository

    async def execute(self, finding: ContradictionFinding) -> None:
        await self.contradictions.save(finding)


@dataclass(frozen=True, slots=True)
class ResolveExpertReview:
    claims: ClaimRepository

    async def execute(self, request: ResolveExpertReviewRequest) -> ClaimVerdictResult:
        claim = await self.claims.get(request.claim_id)
        if claim is None:
            raise ClaimNotFound(f"claim {request.claim_id} not found")
        claim.resolve_review(request.verdict, request.basis)
        await self.claims.save(claim)
        return _verdict_result(claim)


def _infer_claim_type(request: VerifyClaimRequest) -> ClaimType:
    if request.measure is not None or request.asserted_value is not None:
        return ClaimType.QUANTITATIVE
    text = request.text.casefold()
    if any(marker in text for marker in _LEGAL_MARKERS):
        return ClaimType.LEGAL
    if any(marker in text for marker in _CAUSAL_MARKERS):
        return ClaimType.CAUSAL
    return ClaimType.QUALITATIVE


def _verdict_result(claim: Claim) -> ClaimVerdictResult:
    verification = claim.verification
    return ClaimVerdictResult(
        claim_id=str(claim.id),
        verdict=claim.verdict,
        path=verification.path if verification is not None else path_for(claim.type),
        claim_type=claim.type,
        sources=verification.sources if verification is not None else (),
        delta=verification.delta if verification is not None else None,
    )


def _figure_result(figure: ReferenceFigure) -> ReferenceFigureResult:
    return ReferenceFigureResult(
        figure_id=str(figure.id),
        measure=figure.measure.measure,
        unit=figure.measure.unit,
        period=figure.measure.period,
        geography=figure.measure.geography,
        value=figure.value,
        tier=figure.tier.value,
        as_of=figure.as_of.isoformat(),
        source_id=figure.source_id,
    )
