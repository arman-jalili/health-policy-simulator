"""Use-case request DTOs (contract frozen, issue #164)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from claim_validation.domain.values import ClaimId, ClaimType, MeasureReference, VerificationVerdict


@dataclass(frozen=True, slots=True)
class VerifyClaimRequest:
    text: str
    claim_type: ClaimType | None = None
    measure: MeasureReference | None = None
    asserted_value: Decimal | None = None


@dataclass(frozen=True, slots=True)
class FlagUnsupportedAssertionRequest:
    claim_id: ClaimId
    reason: str


@dataclass(frozen=True, slots=True)
class GetClaimRequest:
    claim_id: ClaimId


@dataclass(frozen=True, slots=True)
class RegisterReferenceFigureRequest:
    measure: MeasureReference
    value: Decimal
    tier: str
    as_of: str
    source_id: str


@dataclass(frozen=True, slots=True)
class ListReferenceFiguresRequest:
    measure: MeasureReference | None = None


@dataclass(frozen=True, slots=True)
class ListContradictionsRequest:
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResolveExpertReviewRequest:
    claim_id: ClaimId
    verdict: VerificationVerdict
    basis: str
