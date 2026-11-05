"""In-memory adapters for the database-less local/demo family (issue #178)."""

from __future__ import annotations

from claim_validation.domain.claim import Claim
from claim_validation.domain.entities import ContradictionFinding
from claim_validation.domain.values import (
    ClaimId,
    MeasureReference,
    ReferenceFigure,
    ReferenceFigureId,
)


class InMemoryClaimRepository:
    def __init__(self, claims: list[Claim] | None = None) -> None:
        self._claims = {claim.id: claim for claim in (claims or [])}

    async def get(self, claim_id: ClaimId) -> Claim | None:
        return self._claims.get(claim_id)

    async def save(self, claim: Claim) -> None:
        self._claims[claim.id] = claim

    async def verified_for_measure(self, measure: MeasureReference) -> list[Claim]:
        return [
            claim
            for claim in self._claims.values()
            if claim.measure == measure and claim.verdict.value in {"verified", "contradicted"}
        ]

    async def all_claims(self) -> list[Claim]:
        return list(self._claims.values())


class InMemoryReferenceFigureRepository:
    def __init__(self, figures: list[ReferenceFigure] | None = None) -> None:
        self._figures = {figure.id: figure for figure in (figures or [])}

    async def find(self, measure: MeasureReference) -> ReferenceFigure | None:
        for figure in self._figures.values():
            if figure.measure == measure:
                return figure
        return None

    async def register(self, figure: ReferenceFigure) -> None:
        self._figures[figure.id] = figure

    async def get(self, figure_id: ReferenceFigureId) -> ReferenceFigure | None:
        return self._figures.get(figure_id)

    async def list_all(self) -> list[ReferenceFigure]:
        return list(self._figures.values())


class InMemoryContradictionRepository:
    def __init__(self) -> None:
        self._findings: list[ContradictionFinding] = []

    async def save(self, finding: ContradictionFinding) -> None:
        self._findings.append(finding)

    async def list_for_claim(self, claim_id: ClaimId) -> list[ContradictionFinding]:
        return [
            finding
            for finding in self._findings
            if claim_id in (finding.claim_id_a, finding.claim_id_b)
        ]

    async def list_all(self) -> list[ContradictionFinding]:
        return list(self._findings)
