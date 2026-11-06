"""Stable error codes of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Invariants, Acceptance Criteria)

Every gate has its own code so a client can branch without reading wording (ADR-004). The two
publication-gate failures are audit-critical: they prove the gate ran.
"""

from __future__ import annotations

from collections.abc import Sequence

from decision_brief.domain.values import SectionKind
from shared.errors import (
    AppError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)


class IncompleteBrief(ValidationFailedError):
    """Fewer than the eight mandated sections; the missing kinds are named (AC 1)."""

    code = "INCOMPLETE_BRIEF"

    def __init__(self, missing: Sequence[SectionKind | str]) -> None:
        self.missing: tuple[str, ...] = tuple(str(item) for item in missing)
        super().__init__(f"brief is missing required sections: {', '.join(self.missing)}")


class UnresolvedCitation(ValidationFailedError):
    """A citation did not resolve to a passage provenance; publication is blocked (AC 2)."""

    code = "UNRESOLVED_CITATION"

    def __init__(self, brief_id: str, passage_id: str) -> None:
        self.brief_id = brief_id
        self.passage_id = passage_id
        super().__init__(
            f"citation {passage_id} of brief {brief_id} is unresolved; publication is blocked"
        )


class DisclosureMissing(ValidationFailedError):
    """A required disclosure is absent; publication is refused (AC 3, AC 4)."""

    code = "DISCLOSURE_MISSING"

    def __init__(self, brief_id: str, missing: str) -> None:
        self.brief_id = brief_id
        self.missing = missing
        super().__init__(f"brief {brief_id} omits the required disclosure {missing!r}")


class StatementWithoutCitation(ValidationFailedError):
    """A statement marked ``evidenced`` carries no citation (AC 5, invariant 5)."""

    code = "STATEMENT_WITHOUT_CITATION"

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__("an evidenced statement must cite at least one passage")


class PublishedBriefIsImmutable(ConflictError):
    """A published brief was mutated; a successor version is required (AC 6, invariant 3)."""

    code = "PUBLISHED_BRIEF_IMMUTABLE"

    def __init__(self, brief_id: str) -> None:
        self.brief_id = brief_id
        super().__init__(f"brief {brief_id} is published and immutable; create a new version")


class BlockedOutcomeMisrendered(ValidationFailedError):
    """A veto-blocked topic was rendered as a recommendation (AC 9, invariant 8)."""

    code = "BLOCKED_OUTCOME_MISRENDERED"

    def __init__(self, topic: str) -> None:
        self.topic = topic
        super().__init__(f"veto-blocked topic {topic!r} must render as blocked, not as consensus")


class BriefReproductionMismatch(ConflictError):
    """Regeneration from the run log did not reproduce the published artefact (AC 8)."""

    code = "BRIEF_REPRODUCTION_MISMATCH"

    def __init__(self, run_id: str, section: str) -> None:
        self.run_id = run_id
        self.section = section
        super().__init__(f"regenerated brief for run {run_id} differs in section {section!r}")


class BriefNotFound(NotFoundError):
    """The requested brief does not exist in this context."""

    code = "BRIEF_NOT_FOUND"


class BriefNotPublished(ConflictError):
    """Versioning or citation listing requires a published predecessor."""

    code = "BRIEF_NOT_PUBLISHED"


class BriefGateUnavailable(AppError):
    """A publication gate is not bound; publication fails closed and can never skip the gate."""

    code = "BRIEF_GATE_UNAVAILABLE"
    status_code = 503
    default_message = "a decision brief publication gate is not wired"
