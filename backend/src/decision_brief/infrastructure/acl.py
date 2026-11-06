"""ACL and gate adapters of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Dependencies, Wiring Contract)

These are the only places where an upstream published shape becomes a local projection. Bodies are
frozen stubs: an adapter that cannot map its input must fail closed, never return an empty
projection that would make an incomplete brief look complete.
"""

from __future__ import annotations

from collections.abc import Sequence

from decision_brief.application.dto import CitationResolution
from decision_brief.domain.projections import ConsensusProjection, RunProjection
from decision_brief.domain.values import PassageId, RunId


class NegotiationHistoryAcl:
    """Map NegotiationSession published views to the local run projection (sections 1-5)."""

    async def load(self, run_id: RunId) -> RunProjection | None:
        """Return ``None`` when the run is unknown or still open; never a partial projection."""
        raise NotImplementedError(
            "NegotiationHistoryAcl.load is implemented by "
            "issue-decision-brief-aggregate-root-decisionbrief"
        )


class ConsensusViewAcl:
    """Map the ConsensusAnalysis ``ConsensusView`` to the local consensus projection (6-8)."""

    async def load(self, run_id: RunId) -> ConsensusProjection | None:
        """Return ``None`` when no derived consensus exists for the run."""
        raise NotImplementedError(
            "ConsensusViewAcl.load is implemented by "
            "issue-decision-brief-aggregate-root-decisionbrief"
        )


class EvidenceCorpusCitationResolver:
    """Resolve passage ids against the EvidenceCorpus published passages (AC 2)."""

    async def resolve(self, passage_ids: Sequence[PassageId]) -> CitationResolution:
        """Return every resolved provenance and every id that does not resolve."""
        raise NotImplementedError(
            "EvidenceCorpusCitationResolver.resolve is implemented by "
            "issue-decision-brief-citation-gate"
        )


class GovernanceProvenanceGate:
    """Require GovernanceCompliance disclosures before publication (AC 3, 4, 11)."""

    async def assert_disclosed(self, run_id: RunId) -> None:
        """Raise when a required disclosure is absent; never silently pass."""
        raise NotImplementedError(
            "GovernanceProvenanceGate.assert_disclosed is implemented by "
            "issue-decision-brief-rejected-proposals"
        )
