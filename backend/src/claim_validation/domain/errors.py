"""Stable error codes of ClaimValidation (contract frozen, issue #164)."""

from __future__ import annotations

from shared.errors import ConflictError, NotFoundError, ValidationFailedError


class PathNotApplicable(ValidationFailedError):
    """A verification path cannot be applied to the claim's type (invariant 8)."""

    code = "PATH_NOT_APPLICABLE"

    def __init__(self, claim_id: str, claim_type: str, path: str) -> None:
        self.claim_id = claim_id
        self.claim_type = claim_type
        self.path = path
        super().__init__(f"path {path} is not applicable to {claim_type} claim {claim_id}")


class ReferenceFigureNotAuthoritative(ValidationFailedError):
    """Press-tier values are never reference figures (invariant 6)."""

    code = "REFERENCE_FIGURE_NOT_AUTHORITATIVE"


class ReferenceMeasureMismatch(ValidationFailedError):
    """A figure cannot be compared across measure identities."""

    code = "REFERENCE_MEASURE_MISMATCH"


class ReviewNotEscalated(ConflictError):
    """Only ambiguous claims accept an expert review verdict (invariant 7)."""

    code = "REVIEW_NOT_ESCALATED"


class ClaimNotFound(NotFoundError):
    """The requested claim does not exist in this context."""

    code = "CLAIM_NOT_FOUND"
