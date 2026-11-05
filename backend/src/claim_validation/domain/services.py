"""Domain services of ClaimValidation (issue #165)."""

from __future__ import annotations

from decimal import Decimal

from claim_validation.domain.values import (
    CausalSupport,
    ClaimType,
    MeasureReference,
    ToleranceBand,
    VerificationPath,
)


class ResolveMeasureIdentity:
    """Normalise measure, unit, period and geography into one identity."""

    def resolve(self, measure: str, unit: str, period: str, geography: str) -> MeasureReference:
        raise NotImplementedError("implemented by issue #177")


class FigureComparison:
    """Pure arithmetic comparison with a tolerance band."""

    def compare(
        self,
        asserted: Decimal,
        reference: Decimal,
        band: ToleranceBand,
    ) -> tuple[bool, Decimal]:
        delta = abs(asserted - reference)
        return band.contains(asserted, reference), delta


class ContradictionDetector:
    """Detect incompatible figures for the same measure and period."""

    def is_contradiction(self, a: Decimal, b: Decimal, band: ToleranceBand) -> bool:
        return not band.contains(a, b)


class CausalAppraiser:
    """Appraise causal support; the result never becomes a verified fact."""

    def appraise(self, support: CausalSupport | None) -> CausalSupport:
        if support is None:
            return CausalSupport.UNADDRESSED
        return support


_PATH_BY_TYPE = {
    ClaimType.QUANTITATIVE: VerificationPath.QUANTITATIVE,
    ClaimType.LEGAL: VerificationPath.LEGAL,
    ClaimType.CAUSAL: VerificationPath.CAUSAL,
    ClaimType.QUALITATIVE: VerificationPath.QUALITATIVE,
}


def path_for(claim_type: ClaimType) -> VerificationPath:
    """Select the only legal path for a claim type."""
    return _PATH_BY_TYPE[claim_type]
