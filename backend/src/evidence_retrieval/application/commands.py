"""Application-layer request DTOs (commands and queries) of EvidenceRetrieval.

Canonical: .pi/architecture/modules/evidence-retrieval.md

Frozen interface: one request object per use case, so adding a parameter never changes a service
signature that callers already implement. Framework-free on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass

from evidence_corpus.domain.values import ClaimType
from evidence_retrieval.domain.values import DEFAULT_RESULT_LIMIT, RecencyPolicy


@dataclass(frozen=True, slots=True)
class SearchEvidenceCandidatesRequest:
    """Retrieve candidates for one claim from one pinned snapshot."""

    claim: str
    claim_type: ClaimType
    snapshot_id: str
    limit: int = DEFAULT_RESULT_LIMIT


@dataclass(frozen=True, slots=True)
class AssembleEvidencePackRequest:
    """Build and freeze one balanced evidence pack."""

    claim: str
    claim_type: ClaimType
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class GetEvidencePackRequest:
    pack_id: str


@dataclass(frozen=True, slots=True)
class GetScoreBreakdownRequest:
    pack_id: str


@dataclass(frozen=True, slots=True)
class ApplyRecencyPolicyRequest:
    """Re-score a frozen pack under a different recency policy, producing a new version."""

    pack_id: str
    policy: RecencyPolicy
