"""Claim aggregate (contract frozen, issue #164)."""

from __future__ import annotations

from dataclasses import dataclass, field

from claim_validation.domain.entities import ClaimVerification, ExpertReview
from claim_validation.domain.events import DomainEvent
from claim_validation.domain.values import (
    ClaimId,
    ClaimType,
    MeasureReference,
    VerificationEvidence,
    VerificationPath,
    VerificationVerdict,
)


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
        raise NotImplementedError("implemented by issue #165")

    def mark_unsupported(self, reason: str) -> None:
        raise NotImplementedError("implemented by issue #175")

    def escalate(self, question: str) -> None:
        raise NotImplementedError("implemented by issue #174")

    def resolve_review(self, verdict: VerificationVerdict, basis: str) -> None:
        raise NotImplementedError("implemented by issue #174")

    def drain_events(self) -> list[DomainEvent]:
        raise NotImplementedError("implemented by issue #165")
