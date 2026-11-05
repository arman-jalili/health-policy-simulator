"""Domain services of ClaimValidation (contract frozen, issue #164)."""

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
        raise NotImplementedError("implemented by issue #171")


class ContradictionDetector:
    """Detect incompatible figures for the same measure and period."""

    def is_contradiction(self, a: Decimal, b: Decimal, band: ToleranceBand) -> bool:
        raise NotImplementedError("implemented by issue #172")


class CausalAppraiser:
    """Appraise causal support; the result never becomes a verified fact."""

    def appraise(self, support: CausalSupport) -> CausalSupport:
        raise NotImplementedError("implemented by issue #169")


def path_for(claim_type: ClaimType) -> VerificationPath:
    """Select the only legal path for a claim type."""
    raise NotImplementedError("implemented by issue #168")
