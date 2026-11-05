"""Domain-owned repository interfaces (contract frozen, issue #164)."""

from __future__ import annotations

from typing import Protocol

from claim_validation.domain.claim import Claim
from claim_validation.domain.entities import ContradictionFinding
from claim_validation.domain.values import (
    ClaimId,
    MeasureReference,
    ReferenceFigure,
    ReferenceFigureId,
)


class ClaimRepository(Protocol):
    async def get(self, claim_id: ClaimId) -> Claim | None: ...

    async def save(self, claim: Claim) -> None: ...

    async def verified_for_measure(self, measure: MeasureReference) -> list[Claim]: ...

    async def all_claims(self) -> list[Claim]: ...


class ReferenceFigureRepository(Protocol):
    async def find(self, measure: MeasureReference) -> ReferenceFigure | None: ...

    async def register(self, figure: ReferenceFigure) -> None: ...

    async def get(self, figure_id: ReferenceFigureId) -> ReferenceFigure | None: ...

    async def list_all(self) -> list[ReferenceFigure]: ...


class ContradictionRepository(Protocol):
    async def save(self, finding: ContradictionFinding) -> None: ...

    async def list_for_claim(self, claim_id: ClaimId) -> list[ContradictionFinding]: ...
