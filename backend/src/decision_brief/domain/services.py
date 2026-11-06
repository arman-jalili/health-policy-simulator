"""Frozen domain services of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Service classification)

Classification is frozen here for every named service of the context, including the ports whose
adapters live in ``infrastructure/`` and the renderer that lives in ``interfaces/``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.projections import ConsensusProjection, RunProjection
from decision_brief.domain.values import SimulationDisclaimer, TopicOutcome

SERVICE_CLASSIFICATION: Mapping[str, str] = MappingProxyType(
    {
        "PublishDecisionBrief": "application",
        "VersionDecisionBrief": "application",
        "GetDecisionBrief": "application",
        "ListBriefVersions": "application",
        "ListCitations": "application",
        "BriefProjectionBuilder": "domain",
        "ReproductionChecker": "domain",
        "OutcomeHonestyPolicy": "domain",
        "CitationResolver": "infrastructure",
        "ProvenanceDisclosureGate": "infrastructure",
        "BriefRenderer": "interfaces",
    }
)
"""Where every service of this context belongs (AC: service classification)."""


@runtime_checkable
class BriefProjectionBuilder(Protocol):
    """Pure assembly of the eight sections from local projections; no I/O in the mapping rules."""

    def build(
        self,
        *,
        run: RunProjection,
        consensus: ConsensusProjection,
        disclaimer: SimulationDisclaimer,
    ) -> DecisionBrief: ...


@runtime_checkable
class ReproductionChecker(Protocol):
    """Prove the artefact is a projection: regeneration reproduces it (invariant 7, AC 8)."""

    def assert_reproduces(self, published: DecisionBrief, regenerated: DecisionBrief) -> None: ...


@runtime_checkable
class OutcomeHonestyPolicy(Protocol):
    """A veto-blocked or ambiguous topic is stated as such, never smoothed into agreement (AC 9)."""

    def assert_honest(self, outcomes: Sequence[TopicOutcome]) -> None: ...
