"""ACL and gate adapters of DecisionBrief.

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Dependencies, Wiring Contract)

These are the only places where an upstream published shape becomes a local projection. An adapter
that cannot map its input fails closed, never returning an empty projection that would make an
incomplete brief look complete.
"""

from __future__ import annotations

from collections.abc import Sequence

from decision_brief.application.dto import CitationResolution
from decision_brief.domain.projections import ConsensusProjection, RunProjection
from decision_brief.domain.values import (
    CitationProvenance,
    CitationReference,
    PassageId,
    RunId,
)
from evidence_corpus.application.commands import ResolvePassageRequest
from evidence_corpus.application.services import ResolvePassage
from evidence_corpus.domain.errors import PassageNotFound
from evidence_corpus.domain.published import PassageView


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
    """Resolve passage ids through the EvidenceCorpus ``ResolvePassage`` use case (AC 2).

    A passage the corpus cannot resolve is reported as unresolved; it is never invented, and a
    missing adapter is a wiring failure rather than an empty resolution.
    """

    def __init__(self, resolve_passage: ResolvePassage) -> None:
        self._passages = resolve_passage

    async def resolve(self, passage_ids: Sequence[PassageId]) -> CitationResolution:
        """Return every resolved citation and every id that does not resolve, in input order."""
        resolved: list[CitationReference] = []
        unresolved: list[PassageId] = []
        for passage_id in passage_ids:
            try:
                view = await self._passages.execute(
                    ResolvePassageRequest(passage_id=str(passage_id))
                )
            except PassageNotFound:
                unresolved.append(passage_id)
                continue
            resolved.append(_to_citation(view))
        return CitationResolution(resolved=tuple(resolved), unresolved=tuple(unresolved))


def _to_citation(view: PassageView) -> CitationReference:
    """Map the published passage to a resolved citation; the quote is the citable span."""
    provenance = CitationProvenance(
        outlet=view.provenance.outlet,
        published_on=view.provenance.published_on,
        medium=view.provenance.medium,
        page_from=view.provenance.page_from,
        page_to=view.provenance.page_to,
        source_uri=view.provenance.source_uri,
    )
    return CitationReference(
        passage_id=PassageId(view.passage_id),
        provenance=provenance,
        quote=view.text,
    )


class GovernanceProvenanceGate:
    """Require GovernanceCompliance disclosures before publication (AC 3, 4, 11)."""

    async def assert_disclosed(self, run_id: RunId) -> None:
        """Raise when a required disclosure is absent; never silently pass."""
        raise NotImplementedError(
            "GovernanceProvenanceGate.assert_disclosed is implemented by "
            "issue-decision-brief-rejected-proposals"
        )
