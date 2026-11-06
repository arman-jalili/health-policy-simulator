"""Fail-closed stand-ins for ports the runtime has not bound yet (issue #345).

A publication gate that is not wired must stop publication, never be skipped. Each class below
raises :class:`BriefGateUnavailable` (503, ``BRIEF_GATE_UNAVAILABLE``) with the port it stands in
for, so a partially wired deployment cannot publish a brief that skipped a gate. The
runtime-integration issue replaces these with real ACLs.
"""

from __future__ import annotations

from collections.abc import Sequence

from decision_brief.application.dto import CitationResolution
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.errors import BriefGateUnavailable
from decision_brief.domain.projections import ConsensusProjection, RunProjection
from decision_brief.domain.values import PassageId, RunId


class UnwiredHistorySource:
    """Stand-in for the NegotiationSession run-history ACL."""

    async def load(self, run_id: RunId) -> RunProjection | None:
        raise BriefGateUnavailable(
            f"run history port is not wired; cannot project the brief of {run_id}"
        )


class UnwiredConsensusSource:
    """Stand-in for the ConsensusAnalysis view ACL."""

    async def load(self, run_id: RunId) -> ConsensusProjection | None:
        raise BriefGateUnavailable(
            f"consensus port is not wired; cannot project the brief of {run_id}"
        )


class UnwiredCitationResolver:
    """Stand-in for the EvidenceCorpus citation resolver."""

    async def resolve(self, passage_ids: Sequence[PassageId]) -> CitationResolution:
        raise BriefGateUnavailable("citation resolver port is not wired; publication is blocked")


class UnwiredProvenanceGate:
    """Stand-in for the GovernanceCompliance disclosure gate (AC 11: the gate cannot be skipped)."""

    async def assert_disclosed(self, run_id: RunId) -> None:
        raise BriefGateUnavailable(
            f"governance provenance port is not wired; publication of {run_id} is blocked"
        )


class UnwiredProjectionBuilder:
    """Stand-in for the projection builder adapter."""

    def build(
        self,
        *,
        run: RunProjection,
        consensus: ConsensusProjection,
        disclaimer: object,
    ) -> DecisionBrief:
        raise BriefGateUnavailable("projection builder port is not wired; nothing can be assembled")
