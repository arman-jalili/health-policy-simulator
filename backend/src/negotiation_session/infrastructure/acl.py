"""ACL adapters of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (ACL purity, Wiring Contract)

These are the only places where an upstream published view becomes a domain value. In particular
``EvidencePackView`` becomes ``ClaimEvidence``: passage id, stance and provenance — scores, hit
lists and embedding vectors are dropped. The domain never imports an upstream module (AC 12).
"""

from __future__ import annotations

from collections.abc import Sequence

from claim_validation.interfaces.published import ClaimVerdictView
from evidence_retrieval.interfaces.published import EvidencePackView
from governance_compliance.interfaces.published import GuardVerdictView
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
        raise NotImplementedError("EvidencePackAcl.to_claim_evidence is implemented by issue #297")


class StakeholderProfileAcl:
    """Map the partner contract to the domain's ``StakeholderBinding``."""

    def to_binding(
        self,
        view: StakeholderProfileView,
        *,
        persona_version: str = "",
        allowed_evidence_tiers: Sequence[str] = (),
    ) -> StakeholderBinding:
        raise NotImplementedError("StakeholderProfileAcl.to_binding is implemented by issue #297")


class ClaimVerdictAcl:
    """Verdict gate: only verified or explicitly unsupported claims enter an argument."""

    def accepts(self, verdict: ClaimVerdictView) -> bool:
        raise NotImplementedError("ClaimVerdictAcl.accepts is implemented by issue #297")


class GovernanceGuardAdapter:
    """Pre-persistence guard. It fails closed when the upstream guard is unbound (AC 14)."""

    async def enforce(
        self,
        text: str,
        *,
        run_id: RunId,
        stakeholder_id: StakeholderId,
        invocation_id: InvocationId | None = None,
    ) -> GuardVerdictView:
        raise NotImplementedError("GovernanceGuardAdapter.enforce is implemented by issue #299")
