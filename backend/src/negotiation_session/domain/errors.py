"""Stable error codes of NegotiationSession (contract frozen, issue #282).

Every failure that crosses the HTTP boundary renders as the uniform envelope
``{code, message, details, trace_id}`` (ADR-004). Each class names the invariant and the issue
whose tests prove it.
"""

from __future__ import annotations

from shared.errors import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationFailedError,
)


class SimulationRunNotFound(NotFoundError):
    """No run exists for the supplied id."""

    code = "SIMULATION_RUN_NOT_FOUND"


class PositionNotFound(NotFoundError):
    """No open position exists for this (stakeholder, topic)."""

    code = "POSITION_NOT_FOUND"


class NegotiationRoundNotFound(NotFoundError):
    """The run has no such round."""

    code = "ROUND_NOT_FOUND"


class PhaseRegression(ConflictError):
    """A command tried to move the phase backwards or continue a closed run (invariant 9)."""

    code = "PHASE_REGRESSION"


class ClosedRunImmutable(ConflictError):
    """A closed run is immutable; further analysis is a projection (AC 10)."""

    code = "CLOSED_RUN_IMMUTABLE"


class RoundStillOpen(ConflictError):
    """A new round cannot open while the previous one has not been closed."""

    code = "ROUND_STILL_OPEN"


class RoundCloseGuardViolation(ConflictError):
    """A round cannot close while a bound stakeholder has neither a turn nor an abstention."""

    code = "ROUND_CLOSE_GUARD_VIOLATION"


class RoundLearningMissing(ValidationFailedError):
    """A round cannot close without its ``RoundLearning`` record (AC 9)."""

    code = "ROUND_LEARNING_MISSING"


class RevisionWithoutCause(ConflictError):
    """A position revision cited no argument and no evidence pack (AC 3)."""

    code = "REVISION_WITHOUT_CAUSE"


class ArgumentWithoutEvidence(ValidationFailedError):
    """An argument cited no evidence and was not flagged unsupported (AC 5)."""

    code = "ARGUMENT_WITHOUT_EVIDENCE"


class TurnNotAvailable(ConflictError):
    """The stakeholder has no floor for this topic in the current round (AC 6)."""

    code = "TURN_NOT_AVAILABLE"


class DuplicateTurn(ConflictError):
    """A duplicate turn on the same topic in one round is refused (AC 6)."""

    code = "DUPLICATE_TURN"


class RoundCapExceeded(ConflictError):
    """The round cap is reached; the next command must terminate the run (AC 7)."""

    code = "ROUND_CAP_EXCEEDED"


class CoalitionWithoutOffer(ConflictError):
    """A coalition named a stakeholder who never received an offer (AC 8)."""

    code = "COALITION_WITHOUT_OFFER"


class InvalidCoalitionOfferTransition(ConflictError):
    """A coalition offer can only move offered → accepted | declined."""

    code = "INVALID_COALITION_OFFER_TRANSITION"


class StakeholderNotBound(ValidationFailedError):
    """The stakeholder is not bound to this run."""

    code = "STAKEHOLDER_NOT_BOUND"


class ClaimVerdictRejected(ValidationFailedError):
    """A claim was refused by the ClaimValidation verdict gate before acceptance."""

    code = "CLAIM_VERDICT_REJECTED"


class GovernanceGuardUnavailable(ServiceUnavailableError):
    """The pre-persistence guard is unbound; writes fail closed, never pass (AC 14)."""

    code = "GOVERNANCE_GUARD_UNAVAILABLE"
