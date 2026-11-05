"""Repository adapter exports (contract frozen, issue #164)."""

from claim_validation.domain.repositories import (
    ClaimRepository,
    ContradictionRepository,
    ReferenceFigureRepository,
)

__all__ = ["ClaimRepository", "ContradictionRepository", "ReferenceFigureRepository"]
