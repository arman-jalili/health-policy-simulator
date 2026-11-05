"""Use-case result DTOs (contract frozen, issue #164)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from claim_validation.domain.values import (
    ClaimType,
    VerificationPath,
    VerificationVerdict,
)


@dataclass(frozen=True, slots=True)
class ClaimVerdictResult:
    claim_id: str
    verdict: VerificationVerdict
    path: VerificationPath
    claim_type: ClaimType
    sources: tuple[str, ...]
    delta: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ClaimDetailResult:
    claim_id: str
    text: str
    claim_type: ClaimType
    verdict: VerificationVerdict
    path: VerificationPath | None
    sources: tuple[str, ...]
    review_verdict: VerificationVerdict | None
    review_basis: str | None


@dataclass(frozen=True, slots=True)
class ReferenceFigureResult:
    figure_id: str
    measure: str
    unit: str
    period: str
    geography: str
    value: Decimal
    tier: str
    as_of: str
    source_id: str


@dataclass(frozen=True, slots=True)
class ContradictionResult:
    finding_id: str
    claim_id_a: str
    claim_id_b: str
    measure: str
    delta: Decimal
