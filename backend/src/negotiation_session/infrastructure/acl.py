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
    EvidencePackId,
    InvocationId,
    ProvenanceRef,
    RunId,
    StakeholderBinding,
    StakeholderId,
    TopicRef,
)
from stakeholder_model.interfaces.published import StakeholderProfileView


class EvidencePackAcl:
    """Map a frozen evidence pack to the vector-free domain references."""

    def to_claim_evidence(self, view: EvidencePackView) -> list[ClaimEvidence]:
        return [
            ClaimEvidence(
                evidence_id=EvidencePackId(view.pack_id),
                passage_id=candidate.passage_id,
                stance=str(candidate.stance),
                provenance=(
                    ProvenanceRef(
                        source_id=view.snapshot_id,
                        source_uri=candidate.provenance.source_uri,
                        outlet=candidate.provenance.outlet,
                        published_on=candidate.provenance.published_on,
                    )
                    if candidate.provenance is not None
                    else None
                ),
            )
            for candidate in view.candidates
        ]


class StakeholderProfileAcl:
    """Map the partner contract to the domain's ``StakeholderBinding``."""

    def to_binding(
        self,
        view: StakeholderProfileView,
        *,
        persona_version: str = "",
        allowed_evidence_tiers: Sequence[str] = (),
    ) -> StakeholderBinding:
        return StakeholderBinding(
            stakeholder_id=StakeholderId(view.stakeholder_id),
            institution_name=view.identity.name,
            institution_code=view.identity.code,
            interests=tuple(f"{item.topic}: {item.goal}" for item in view.interests),
            constraints=tuple(item.statement for item in view.constraints),
            red_lines=view.red_lines,
            veto_classes=tuple(str(item.proposal_class) for item in view.veto_rights),
            mandate_topics=tuple(TopicRef(topic) for topic in view.mandate_scope.topics),
            profile_version=view.profile_version,
            persona_version=persona_version,
            allowed_evidence_tiers=tuple(allowed_evidence_tiers),
        )


class ClaimVerdictAcl:
    """Verdict gate: only verified or explicitly unsupported claims enter an argument."""

    def accepts(self, verdict: ClaimVerdictView) -> bool:
        """Only verified claims or explicitly unsupported ones enter an argument."""
        return verdict.verdict in {"verified", "unsupported"}


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
