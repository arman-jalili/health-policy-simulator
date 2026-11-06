"""ACL adapters of NegotiationSession (contract frozen, issue #282; wired in #299).

The mapper functions live in ``application/mappers.py`` so the application services share them;
this module keeps the adapter class names the contract froze and implements the guard adapter.
"""

from __future__ import annotations

from collections.abc import Sequence

from claim_validation.interfaces.published import ClaimVerdictView
from evidence_retrieval.interfaces.published import EvidencePackView
from governance_compliance.application.commands import EnforceInstitutionOnlyOutputRequest
from governance_compliance.application.services import EnforceInstitutionOnlyOutput
from governance_compliance.application.values import (
    InvocationId as GovernanceInvocationId,
)
from governance_compliance.application.values import RunId as GovernanceRunId
from governance_compliance.application.values import SpeakerKind
from governance_compliance.interfaces.published import GuardVerdictView
from negotiation_session.application.mappers import (
    binding_from_profile,
    claim_evidence_from_pack,
    claim_is_admissible,
)
from negotiation_session.domain.errors import GovernanceGuardUnavailable
from negotiation_session.domain.values import (
    ClaimEvidence,
    InvocationId,
    RunId,
    StakeholderBinding,
    StakeholderId,
)
from stakeholder_model.interfaces.published import StakeholderProfileView


class EvidencePackAcl:
    """Map a frozen evidence pack to the vector-free domain references."""

    def to_claim_evidence(self, view: EvidencePackView) -> list[ClaimEvidence]:
        return claim_evidence_from_pack(view)


class StakeholderProfileAcl:
    """Map the partner contract to the domain's ``StakeholderBinding``."""

    def to_binding(
        self,
        view: StakeholderProfileView,
        *,
        persona_version: str = "",
        allowed_evidence_tiers: Sequence[str] = (),
    ) -> StakeholderBinding:
        return binding_from_profile(
            view,
            persona_version=persona_version,
            allowed_evidence_tiers=allowed_evidence_tiers,
        )


class ClaimVerdictAcl:
    """Verdict gate: only verified or explicitly unsupported claims enter an argument."""

    def accepts(self, verdict: ClaimVerdictView) -> bool:
        return claim_is_admissible(verdict)


class GovernanceGuardAdapter:
    """Pre-persistence guard; it fails closed when the upstream guard is unbound."""

    def __init__(self, enforce: EnforceInstitutionOnlyOutput | None = None) -> None:
        self._enforce = enforce

    async def enforce(
        self,
        text: str,
        *,
        run_id: RunId,
        stakeholder_id: StakeholderId,
        invocation_id: InvocationId | None = None,
    ) -> GuardVerdictView:
        if self._enforce is None:
            raise GovernanceGuardUnavailable(
                "governance guard is not wired; refusing to persist negotiation text"
            )
        result = await self._enforce.execute(
            EnforceInstitutionOnlyOutputRequest(
                text=text,
                speaker_kind=SpeakerKind.INSTITUTION,
                invocation_id=GovernanceInvocationId(str(invocation_id or "")),
                run_id=GovernanceRunId(str(run_id)),
            )
        )
        from governance_compliance.interfaces.published import to_guard_verdict_view

        return to_guard_verdict_view(result)
