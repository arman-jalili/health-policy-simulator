"""Application services (contract frozen, issue #164)."""

from __future__ import annotations

from dataclasses import dataclass

from claim_validation.application.commands import (
    FlagUnsupportedAssertionRequest,
    GetClaimRequest,
    ListContradictionsRequest,
    ListReferenceFiguresRequest,
    RegisterReferenceFigureRequest,
    ResolveExpertReviewRequest,
    VerifyClaimRequest,
)
from claim_validation.application.dto import (
    ClaimDetailResult,
    ClaimVerdictResult,
    ContradictionResult,
    ReferenceFigureResult,
)
from claim_validation.domain.entities import ContradictionFinding


@dataclass(frozen=True, slots=True)
class VerifyClaim:
    async def execute(self, request: VerifyClaimRequest) -> ClaimVerdictResult:
        raise NotImplementedError("implemented by issue #167")


@dataclass(frozen=True, slots=True)
class FlagUnsupportedAssertion:
    async def execute(self, request: FlagUnsupportedAssertionRequest) -> ClaimVerdictResult:
        raise NotImplementedError("implemented by issue #175")


@dataclass(frozen=True, slots=True)
class GetClaim:
    async def execute(self, request: GetClaimRequest) -> ClaimDetailResult:
        raise NotImplementedError("implemented by issue #178")


@dataclass(frozen=True, slots=True)
class RegisterReferenceFigure:
    async def execute(self, request: RegisterReferenceFigureRequest) -> ReferenceFigureResult:
        raise NotImplementedError("implemented by issue #173")


@dataclass(frozen=True, slots=True)
class ListReferenceFigures:
    async def execute(self, request: ListReferenceFiguresRequest) -> list[ReferenceFigureResult]:
        raise NotImplementedError("implemented by issue #178")


@dataclass(frozen=True, slots=True)
class ListContradictions:
    async def execute(self, request: ListContradictionsRequest) -> list[ContradictionResult]:
        raise NotImplementedError("implemented by issue #172")


@dataclass(frozen=True, slots=True)
class RecordContradiction:
    async def execute(self, finding: ContradictionFinding) -> None:
        raise NotImplementedError("implemented by issue #172")


@dataclass(frozen=True, slots=True)
class ResolveExpertReview:
    async def execute(self, request: ResolveExpertReviewRequest) -> ClaimVerdictResult:
        raise NotImplementedError("implemented by issue #174")
