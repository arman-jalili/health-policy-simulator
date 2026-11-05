"""Evidence adapter used until legal/causal corpus queries are published (issue #178)."""

from __future__ import annotations

from claim_validation.domain.values import ClaimType, VerificationEvidence


class EmptyEvidence:
    """Return no evidence rather than inventing sources; claims stay unsupported/unaddressed."""

    async def evidence_for(self, claim_type: ClaimType, text: str) -> VerificationEvidence:
        return VerificationEvidence(method=f"no_{claim_type.value}_evidence")
