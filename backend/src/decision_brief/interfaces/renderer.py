"""Brief renderers — output format, not domain (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Patterns: Renderer — Strategy)

The JSON document is the frozen wire artefact (AC 10): it always carries the disclaimer and the
model/prompt version reference. ``BRIEF_DOCUMENT_SCHEMA_VERSION`` is part of that contract.
"""

from __future__ import annotations

from typing import ClassVar, Final, Protocol, runtime_checkable

from decision_brief.domain.decision_brief import DecisionBrief

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
        raise NotImplementedError(
            "JsonBriefRenderer.render is implemented by "
            "issue-decision-brief-probabilistic-disclaimer"
        )
