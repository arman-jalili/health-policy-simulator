"""Domain events of ClaimValidation (contract frozen, issue #164)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from claim_validation.domain.values import (
    CausalSupport,
    ClaimType,
    MeasureReference,
    VerificationVerdict,
)


@dataclass(frozen=True, slots=True)
class ClaimExtracted:
    name: ClassVar[str] = "ClaimExtracted"
    claim_id: str
    claim_type: ClaimType
    has_measure: bool


@dataclass(frozen=True, slots=True)
class ClaimVerified:
    name: ClassVar[str] = "ClaimVerified"
    claim_id: str
    reference_id: str
    method: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClaimRejected:
    name: ClassVar[str] = "ClaimRejected"
    claim_id: str
    reference_id: str
    asserted_value: Decimal
    reference_value: Decimal
    delta: Decimal


@dataclass(frozen=True, slots=True)
class UnsupportedAssertionFlagged:
    name: ClassVar[str] = "UnsupportedAssertionFlagged"
    claim_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ContradictionDetected:
    name: ClassVar[str] = "ContradictionDetected"
    claim_id_a: str
    claim_id_b: str
    measure: MeasureReference
    delta: Decimal


@dataclass(frozen=True, slots=True)
class ReferenceFigureRegistered:
    name: ClassVar[str] = "ReferenceFigureRegistered"
    figure_id: str
    measure: MeasureReference
    value: Decimal
    tier: str
    as_of: str


@dataclass(frozen=True, slots=True)
class ClaimEscalatedForReview:
    name: ClassVar[str] = "ClaimEscalatedForReview"
    claim_id: str
    question: str


@dataclass(frozen=True, slots=True)
class ExpertReviewResolved:
    name: ClassVar[str] = "ExpertReviewResolved"
    claim_id: str
    verdict: VerificationVerdict
    basis: str


@dataclass(frozen=True, slots=True)
class ClaimMarkedUnverifiable:
    name: ClassVar[str] = "ClaimMarkedUnverifiable"
    claim_id: str
    claim_type: ClaimType


@dataclass(frozen=True, slots=True)
class CausalClaimAppraised:
    name: ClassVar[str] = "CausalClaimAppraised"
    claim_id: str
    support: CausalSupport
    study_ids: tuple[str, ...]


DomainEvent = (
    ClaimExtracted
    | ClaimVerified
    | ClaimRejected
    | UnsupportedAssertionFlagged
    | ContradictionDetected
    | ReferenceFigureRegistered
    | ClaimEscalatedForReview
    | ExpertReviewResolved
    | ClaimMarkedUnverifiable
    | CausalClaimAppraised
)
