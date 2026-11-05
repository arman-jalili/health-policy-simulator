"""Claim aggregate (issue #165).

Canonical: `.pi/architecture/modules/claim-validation.md`

Verification is type-directed. A causal or qualitative claim can never become ``VERIFIED``; an
unsupported assertion stays visible as ``UNSUPPORTED``; ambiguity is a first-class outcome that only
an expert review can settle.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from claim_validation.domain.entities import ClaimVerification, ExpertReview
from claim_validation.domain.errors import PathNotApplicable, ReviewNotEscalated
from claim_validation.domain.events import (
    CausalClaimAppraised,
    ClaimEscalatedForReview,
    ClaimMarkedUnverifiable,
    ClaimRejected,
    ClaimVerified,
    DomainEvent,
    ExpertReviewResolved,
    UnsupportedAssertionFlagged,
)
from claim_validation.domain.services import CausalAppraiser, FigureComparison, path_for
from claim_validation.domain.values import (
    ClaimId,
    ClaimType,
    MeasureReference,
    ReviewId,
    ToleranceBand,
    VerificationEvidence,
    VerificationPath,
    VerificationVerdict,
)
from shared.ids import new_id

_DEFAULT_BAND = ToleranceBand()


@dataclass(eq=False, slots=True)
class Claim:
    id: ClaimId
    text: str
    type: ClaimType
    measure: MeasureReference | None = None
    verdict: VerificationVerdict = VerificationVerdict.PENDING
    verification: ClaimVerification | None = None
    review: ExpertReview | None = None
    events: list[DomainEvent] = field(default_factory=list)

    def verify(self, path: VerificationPath, evidence: VerificationEvidence) -> None:
        """Apply the only legal path for this claim type."""
        expected = path_for(self.type)
        if path is not expected:
            raise PathNotApplicable(str(self.id), self.type.value, path.value)

        if self.type is ClaimType.QUALITATIVE:
            self._mark_unverifiable()
            return
        if self.type is ClaimType.CAUSAL:
            self._appraise(evidence)
            return
        if self.type is ClaimType.QUANTITATIVE:
            self._compare_figures(evidence)
            return
        self._compare_provisions(evidence)

    def mark_unsupported(self, reason: str) -> None:
        """Never silently drop a claim; it becomes visibly low-confidence."""
        self.verdict = VerificationVerdict.UNSUPPORTED
        self.verification = ClaimVerification(
            verdict=VerificationVerdict.UNSUPPORTED,
            path=path_for(self.type),
            sources=(),
            method=reason,
        )
        self.events.append(UnsupportedAssertionFlagged(str(self.id), reason))

    def escalate(self, question: str) -> None:
        """Record ambiguity; only an expert review can settle it."""
        self.verdict = VerificationVerdict.AMBIGUOUS
        self.review = ExpertReview(
            id=ReviewId(new_id("rev")),
            question=question,
            verdict=VerificationVerdict.PENDING,
            basis="",
        )
        self.events.append(ClaimEscalatedForReview(str(self.id), question))

    def resolve_review(self, verdict: VerificationVerdict, basis: str) -> None:
        """Settle an escalated claim, never a claim that was never escalated."""
        if self.verdict is not VerificationVerdict.AMBIGUOUS or self.review is None:
            raise ReviewNotEscalated(f"claim {self.id} is not escalated")
        if verdict not in (VerificationVerdict.VERIFIED, VerificationVerdict.CONTRADICTED):
            raise ReviewNotEscalated("expert review must settle verified or contradicted")
        self.review = ExpertReview(
            id=self.review.id,
            question=self.review.question,
            verdict=verdict,
            basis=basis,
        )
        self.verdict = verdict
        self.events.append(ExpertReviewResolved(str(self.id), verdict, basis))

    def drain_events(self) -> list[DomainEvent]:
        drained = list(self.events)
        self.events.clear()
        return drained

    def _compare_figures(self, evidence: VerificationEvidence) -> None:
        reference = evidence.reference_figure
        asserted = evidence.asserted_value
        if reference is None:
            self.escalate(f"no reference figure for measure {self.measure}")
            return
        if asserted is None:
            self.mark_unsupported("no asserted value")
            return
        if self.measure is not None and self.measure != reference.measure:
            self.escalate("asserted measure does not match the reference measure")
            return
        within, delta = FigureComparison().compare(asserted, reference.value, _DEFAULT_BAND)
        sources = tuple(dict.fromkeys((*evidence.sources, reference.source_id)))
        if within:
            self.verdict = VerificationVerdict.VERIFIED
            self.verification = ClaimVerification(
                verdict=VerificationVerdict.VERIFIED,
                path=VerificationPath.QUANTITATIVE,
                sources=sources,
                method="reference_figure",
                reference_id=reference.id,
                asserted_value=asserted,
                reference_value=reference.value,
                delta=delta,
            )
            self.events.append(
                ClaimVerified(str(self.id), str(reference.id), "reference_figure", sources)
            )
            return
        self.verdict = VerificationVerdict.CONTRADICTED
        self.verification = ClaimVerification(
            verdict=VerificationVerdict.CONTRADICTED,
            path=VerificationPath.QUANTITATIVE,
            sources=sources,
            method="reference_figure",
            reference_id=reference.id,
            asserted_value=asserted,
            reference_value=reference.value,
            delta=delta,
        )
        self.events.append(
            ClaimRejected(
                str(self.id),
                str(reference.id),
                asserted,
                reference.value,
                delta,
            )
        )

    def _compare_provisions(self, evidence: VerificationEvidence) -> None:
        if not evidence.sources:
            self.mark_unsupported("no provision above threshold")
            return
        self.verdict = VerificationVerdict.VERIFIED
        self.verification = ClaimVerification(
            verdict=VerificationVerdict.VERIFIED,
            path=VerificationPath.LEGAL,
            sources=evidence.sources,
            method=evidence.method,
        )
        self.events.append(
            ClaimVerified(str(self.id), evidence.sources[0], evidence.method, evidence.sources)
        )

    def _appraise(self, evidence: VerificationEvidence) -> None:
        support = CausalAppraiser().appraise(evidence.support)
        self.verdict = VerificationVerdict.AMBIGUOUS
        self.verification = ClaimVerification(
            verdict=VerificationVerdict.AMBIGUOUS,
            path=VerificationPath.CAUSAL,
            sources=evidence.study_ids,
            method="study_appraisal",
        )
        self.events.append(CausalClaimAppraised(str(self.id), support, evidence.study_ids))

    def _mark_unverifiable(self) -> None:
        self.verdict = VerificationVerdict.AMBIGUOUS
        self.verification = ClaimVerification(
            verdict=VerificationVerdict.AMBIGUOUS,
            path=VerificationPath.QUALITATIVE,
            sources=(),
            method="no_applicable_path",
        )
        self.events.append(ClaimMarkedUnverifiable(str(self.id), self.type))
