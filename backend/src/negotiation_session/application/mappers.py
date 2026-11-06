"""ACL mapping from upstream published views to domain values (issue #297, #299).

Mapping lives here so both the application services and the infrastructure adapters share one
implementation, and ``domain/`` never imports an upstream package.
"""

from __future__ import annotations

from collections.abc import Sequence

from claim_validation.interfaces.published import ClaimVerdictView
from evidence_retrieval.interfaces.published import EvidencePackView
from governance_compliance.interfaces.published import GuardVerdictView
from negotiation_session.domain.values import (
    ClaimEvidence,
    EvidencePackId,
    ProvenanceRef,
    StakeholderBinding,
    StakeholderId,
    TopicRef,
)
from stakeholder_model.interfaces.published import StakeholderProfileView

_ACCEPTED_CLAIM_VERDICTS = frozenset({"verified", "unsupported"})


def claim_evidence_from_pack(view: EvidencePackView) -> list[ClaimEvidence]:
    """Drop scores and vectors; keep only resolvable references and provenance."""
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


def binding_from_profile(
    view: StakeholderProfileView,
    *,
    persona_version: str = "",
    allowed_evidence_tiers: Sequence[str] = (),
) -> StakeholderBinding:
    """Map the partner contract to the domain binding vocabulary."""
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


def claim_is_admissible(verdict: ClaimVerdictView) -> bool:
    """Only verified claims or explicitly unsupported ones enter an argument."""
    return verdict.verdict in _ACCEPTED_CLAIM_VERDICTS


def guard_rejected(verdict: GuardVerdictView) -> bool:
    return verdict.decision == "reject"


def guard_rewritten_text(verdict: GuardVerdictView) -> str | None:
    return verdict.rewritten_text
