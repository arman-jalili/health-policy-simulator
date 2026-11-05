"""ClaimValidation-backed figure verdict lookup (GC-005)."""

from __future__ import annotations

from claim_validation.domain.repositories import ClaimRepository
from claim_validation.domain.values import VerificationVerdict
from governance_compliance.application.values import FigureVerdict

_VERDICTS = {
    VerificationVerdict.VERIFIED: FigureVerdict.VERIFIED,
    VerificationVerdict.CONTRADICTED: FigureVerdict.CONTRADICTED,
    VerificationVerdict.UNSUPPORTED: FigureVerdict.UNSUPPORTED,
    VerificationVerdict.AMBIGUOUS: FigureVerdict.AMBIGUOUS,
}


class ClaimValidationFigureVerdicts:
    """Read the reference-figure link from the claim verification record."""

    def __init__(self, claims: ClaimRepository) -> None:
        self._claims = claims

    async def verdict_for(self, reference_figure_id: str) -> FigureVerdict | None:
        for claim in await self._claims.all_claims():
            verification = claim.verification
            if verification is None or verification.reference_id is None:
                continue
            if str(verification.reference_id) == reference_figure_id:
                return _VERDICTS.get(claim.verdict, FigureVerdict.AMBIGUOUS)
        return None


class UnknownFigureVerdicts:
    """Explicit no-source adapter; production wiring must use ClaimValidationFigureVerdicts."""

    async def verdict_for(self, reference_figure_id: str) -> FigureVerdict | None:
        return None
