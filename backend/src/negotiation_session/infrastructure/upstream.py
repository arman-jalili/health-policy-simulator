"""Adapters that bind the negotiation ports to the real upstream contexts (issue #299).

Every adapter is a thin ACL: it calls one upstream use case and maps the published view. None of
them exposes an ORM row, retrieval hit or embedding vector to the domain.
"""

from __future__ import annotations

from collections.abc import Sequence

from claim_validation.application.commands import VerifyClaimRequest
from claim_validation.composition import ClaimValidationContainer
from claim_validation.interfaces.published import ClaimVerdictView, to_verdict_view
from evidence_retrieval.application.commands import GetEvidencePackRequest
from evidence_retrieval.composition import EvidenceRetrievalContainer
from evidence_retrieval.domain.errors import EvidencePackNotFound as RetrievalPackNotFound
from evidence_retrieval.interfaces.published import EvidencePackView, to_published_pack
from negotiation_session.application.ports import InvocationLookup
from negotiation_session.domain.errors import StakeholderNotBound
from negotiation_session.domain.values import (
    ClaimStatement,
    EvidencePackId,
    InvocationId,
    RunId,
    StakeholderId,
)
from shared.errors import ValidationFailedError
from stakeholder_model.application.commands import GetStakeholderRequest
from stakeholder_model.composition import StakeholderModelContainer
from stakeholder_model.domain.errors import StakeholderNotFound
from stakeholder_model.domain.values import StakeholderId as UpstreamStakeholderId
from stakeholder_model.interfaces.published import (
    StakeholderProfileView,
    to_profile_view,
)


class RetrievalEvidencePacks:
    """ACL to EvidenceRetrieval's stored, frozen packs."""

    def __init__(self, retrieval: EvidenceRetrievalContainer) -> None:
        self._retrieval = retrieval

    async def frozen_pack(self, pack_id: EvidencePackId) -> EvidencePackView | None:
        try:
            result = await self._retrieval.get_pack.execute(
                GetEvidencePackRequest(pack_id=str(pack_id))
            )
        except RetrievalPackNotFound:
            return None
        return to_published_pack(result)


class StakeholderProfiles:
    """ACL to StakeholderModel's partner contract."""

    def __init__(self, stakeholders: StakeholderModelContainer) -> None:
        self._stakeholders = stakeholders

    async def profile(self, stakeholder_id: StakeholderId) -> StakeholderProfileView | None:
        try:
            result = await self._stakeholders.get_profile.execute(
                GetStakeholderRequest(stakeholder_id=UpstreamStakeholderId(str(stakeholder_id)))
            )
        except StakeholderNotFound:
            return None
        return to_profile_view(result)

    async def candidates(self) -> Sequence[StakeholderProfileView]:
        registered = await self._stakeholders.repository.all_registered()
        profiles: list[StakeholderProfileView] = []
        for stakeholder in registered:
            view = await self.profile(StakeholderId(str(stakeholder.id)))
            if view is not None:
                profiles.append(view)
        return profiles


class ClaimVerdicts:
    """ACL to ClaimValidation: verdicts gate claims before acceptance."""

    def __init__(self, claims: ClaimValidationContainer) -> None:
        self._claims = claims

    async def verdict_for(self, claim: ClaimStatement) -> ClaimVerdictView:
        result = await self._claims.verify_claim.execute(VerifyClaimRequest(text=claim.text))
        return to_verdict_view(
            claim_id=result.claim_id,
            verdict=result.verdict.value,
            claim_type=result.claim_type.value,
            sources=result.sources,
            delta=result.delta,
        )


class RequiredInvocationLookup:
    """Every argument must name the invocation that produced it (ADR-006, W8)."""

    async def require(self, run_id: RunId, invocation_id: InvocationId) -> None:
        if not str(invocation_id).strip():
            raise ValidationFailedError("an argument requires its invocation id")


__all__ = [
    "ClaimVerdicts",
    "InvocationLookup",
    "RequiredInvocationLookup",
    "RetrievalEvidencePacks",
    "StakeholderNotBound",
    "StakeholderProfiles",
    "ValidationFailedError",
]
