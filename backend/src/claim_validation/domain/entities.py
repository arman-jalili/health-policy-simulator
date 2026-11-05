"""Entities of ClaimValidation (contract frozen, issue #164)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from claim_validation.domain.values import (
    ClaimId,
    ContradictionId,
    MeasureReference,
    ReferenceFigureId,
    ReviewId,
    VerificationPath,
    VerificationVerdict,
)


@dataclass(frozen=True, slots=True)
class ClaimVerification:
    verdict: VerificationVerdict
    path: VerificationPath
    sources: tuple[str, ...]
    method: str
    reference_id: ReferenceFigureId | None = None
    asserted_value: Decimal | None = None
    reference_value: Decimal | None = None
    delta: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ContradictionFinding:
    id: ContradictionId
    claim_id_a: ClaimId
    claim_id_b: ClaimId
    measure: MeasureReference
    delta: Decimal


@dataclass(frozen=True, slots=True)
class ExpertReview:
    id: ReviewId
    question: str
    verdict: VerificationVerdict
    basis: str
