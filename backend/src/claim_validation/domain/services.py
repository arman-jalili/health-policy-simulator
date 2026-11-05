"""Domain services of ClaimValidation (issue #165)."""

from __future__ import annotations

from decimal import Decimal

from claim_validation.domain.entities import ContradictionFinding
from claim_validation.domain.values import (
    CausalSupport,
    ClaimId,
    ClaimType,
    ContradictionId,
    MeasureReference,
    ToleranceBand,
    VerificationPath,
)

_UNITS = {
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "%": "percent",
    "prozent": "percent",
    "percent": "percent",
    "personen": "count",
    "kassenstellen": "count",
    "stellen": "count",
    "tage": "days",
    "tag": "days",
    "days": "days",
}
_GEOGRAPHIES = {
    "at": "AT",
    "aut": "AT",
    "österreich": "AT",
    "oesterreich": "AT",
    "austria": "AT",
}


class ResolveMeasureIdentity:
    """Normalise measure, unit, period and geography into one identity."""

    def resolve(self, measure: str, unit: str, period: str, geography: str) -> MeasureReference:
        normal_measure = " ".join(measure.split()).casefold()
        normal_unit = _UNITS.get(" ".join(unit.split()).casefold(), unit.strip())
        normal_period = " ".join(period.split()).casefold()
        normal_geo = _GEOGRAPHIES.get(
            " ".join(geography.split()).casefold(), geography.strip().upper()
        )
        return MeasureReference(normal_measure, normal_unit, normal_period, normal_geo)


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

    def finding_for(
        self,
        claim_a: object,
        claim_b: object,
        band: ToleranceBand,
    ) -> ContradictionFinding | None:
        """Return a finding when two verified claims disagree for the same measure."""
        from claim_validation.domain.claim import Claim
        from shared.ids import new_id

        if not isinstance(claim_a, Claim) or not isinstance(claim_b, Claim):
            return None
        if claim_a.measure is None or claim_a.measure != claim_b.measure:
            return None
        first = claim_a.verification
        second = claim_b.verification
        if first is None or second is None:
            return None
        if first.asserted_value is None or second.asserted_value is None:
            return None
        if not self.is_contradiction(first.asserted_value, second.asserted_value, band):
            return None
        return ContradictionFinding(
            id=ContradictionId(new_id("con")),
            claim_id_a=ClaimId(str(claim_a.id)),
            claim_id_b=ClaimId(str(claim_b.id)),
            measure=claim_a.measure,
            delta=abs(first.asserted_value - second.asserted_value),
        )


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
