"""Published language of ClaimValidation (contract frozen, issue #164)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ClaimVerdictView:
    """What NegotiationSession/GovernanceCompliance may consume; no vectors or ORM."""

    claim_id: str
    verdict: str
    claim_type: str
    sources: tuple[str, ...]
    delta: Decimal | None = None
