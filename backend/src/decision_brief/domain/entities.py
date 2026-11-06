"""Frozen entities of DecisionBrief (contract frozen #331, validated by #333).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Entity relationship)

``BriefSection`` has ordinal identity inside one brief; ``RejectedProposalRecord`` is the disclosed
refusal. Both are content-immutable. Rejected proposals live on the aggregate (the publication gate
reads them there) and are rendered inside section 5, ``compromise_proposals``.
"""

from __future__ import annotations

from dataclasses import dataclass

from decision_brief.domain.values import SECTION_ORDINAL, CitedStatement, SectionKind


@dataclass(frozen=True, slots=True)
class BriefSection:
    """One of the eight mandated components; content is immutable once published."""

    kind: SectionKind
    ordinal: int
    statements: tuple[CitedStatement, ...] = ()

    def __post_init__(self) -> None:
        expected = SECTION_ORDINAL[self.kind]
        if self.ordinal != expected:
            raise ValueError(
                f"section {self.kind.value!r} belongs at ordinal {expected}, not {self.ordinal}"
            )


@dataclass(frozen=True, slots=True)
class RejectedProposalRecord:
    """Measure that failed to gather support, with the blockers and the recorded reasons."""

    measure: str
    blocking_stakeholders: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.measure.strip():
            raise ValueError("a rejected proposal record requires the measure")
        if not self.blocking_stakeholders:
            raise ValueError("a rejected proposal must name the stakeholders that blocked it")
