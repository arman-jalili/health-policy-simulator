"""Brief renderers — output format, not domain (contract frozen #331, rendered by #344).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Patterns: Renderer — Strategy)

The JSON document is the frozen wire artefact (AC 10): it always carries the disclaimer and the
model/prompt version reference, the eight sections in ordinal order, every citation with its
resolution state and the honestly stated outcomes. ``BRIEF_DOCUMENT_SCHEMA_VERSION`` is part of that
contract. Rendering is a pure projection of the artefact: it never re-derives or re-resolves
anything.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar, Final, Protocol, runtime_checkable

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.values import (
    SECTION_ORDINAL,
    CitationReference,
    CitedStatement,
    SimulationDisclaimer,
    TopicOutcome,
)

BRIEF_DOCUMENT_SCHEMA_VERSION: Final[str] = "1.0"
"""Version of the rendered brief document; a breaking shape change bumps this."""


@runtime_checkable
class BriefRenderer(Protocol):
    """Strategy over the artefact: one brief, two outputs."""

    media_type: ClassVar[str]

    def render(self, brief: DecisionBrief) -> bytes: ...


class JsonBriefRenderer:
    """Render the frozen brief document; PDF rendering stays optional and out of scope."""

    media_type: ClassVar[str] = "application/json"

    def render(self, brief: DecisionBrief) -> bytes:
        """Return the UTF-8 JSON document; field order is the contract's reading order."""
        return json.dumps(
            brief_document(brief),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=False,
        ).encode("utf-8")


def brief_document(brief: DecisionBrief) -> dict[str, Any]:
    """Map the artefact onto the frozen wire document (``BriefResponse``)."""
    return {
        "brief_id": str(brief.id),
        "run_id": str(brief.run_id),
        "status": brief.status.value,
        "version": {
            "number": brief.version.number,
            "run_id": str(brief.version.run_id),
            "snapshot_ref": brief.version.snapshot_ref,
            "generated_at": brief.version.generated_at.isoformat(),
            "previous_version": brief.version.previous_version,
            "reason": brief.version.reason,
        },
        "sections": [
            {
                "kind": section.kind.value,
                "ordinal": section.ordinal,
                "statements": [_statement(statement) for statement in section.statements],
            }
            for _, section in sorted(
                brief.sections.items(), key=lambda item: SECTION_ORDINAL[item[0]]
            )
        ],
        "rejected_proposals": [
            {
                "measure": record.measure,
                "blocking_stakeholders": list(record.blocking_stakeholders),
                "reasons": list(record.reasons),
            }
            for record in brief.rejected_proposals
        ],
        "outcomes": [_outcome(outcome) for outcome in brief.outcomes],
        "disclaimer": _disclaimer(brief.disclaimer),
        "citation_count": brief.citation_count(),
        "schema_version": BRIEF_DOCUMENT_SCHEMA_VERSION,
    }


def _statement(statement: CitedStatement) -> dict[str, Any]:
    return {
        "text": statement.text,
        "status": statement.status.value,
        "claim_ids": list(statement.claim_ids),
        "citations": [_citation(citation) for citation in statement.citations],
    }


def _citation(citation: CitationReference) -> dict[str, Any]:
    provenance = citation.provenance
    return {
        "passage_id": str(citation.passage_id),
        "resolved": citation.is_resolved(),
        "quote": citation.quote,
        "outlet": provenance.outlet if provenance is not None else None,
        "published_on": provenance.published_on.isoformat() if provenance is not None else None,
        "medium": provenance.medium if provenance is not None else None,
        "page_from": provenance.page_from if provenance is not None else None,
        "page_to": provenance.page_to if provenance is not None else None,
        "source_uri": provenance.source_uri if provenance is not None else None,
    }


def _outcome(outcome: TopicOutcome) -> dict[str, Any]:
    return {
        "topic": outcome.topic,
        "kind": outcome.kind.value,
        "blocking_stakeholders": list(outcome.blocking_stakeholders),
        "reason": outcome.reason,
    }


def _disclaimer(disclaimer: SimulationDisclaimer | None) -> dict[str, Any] | None:
    if disclaimer is None:
        return None
    return {
        "text": disclaimer.text,
        "model_reference": disclaimer.model_reference,
        "prompt_version": disclaimer.prompt_version,
    }
