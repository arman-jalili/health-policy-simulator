"""Stable error codes of SimulationOrchestration (contract frozen, issue #205)."""

from __future__ import annotations

from shared.errors import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationFailedError,
)


class SimulationJobNotFound(NotFoundError):
    """No job exists for the supplied id."""

    code = "SIMULATION_JOB_NOT_FOUND"


class SimulationRunNotFound(NotFoundError):
    """No job exists for the supplied run id."""

    code = "SIMULATION_RUN_NOT_FOUND"


class InvalidJobTransition(ConflictError):
    """The requested pause/resume transition is not legal for the current status."""

    code = "INVALID_JOB_TRANSITION"


class RunBudgetExceeded(ConflictError):
    """A pre-call budget check rejected the invocation."""

    code = "RUN_BUDGET_EXHAUSTED"


class UnknownModel(ValidationFailedError):
    """The model id has no price entry; boot and invocation both fail closed."""

    code = "UNKNOWN_MODEL"


class PromptNotFound(NotFoundError):
    """No prompt template exists for the requested name/version."""

    code = "PROMPT_NOT_FOUND"


class InvalidPromptTemplate(ValidationFailedError):
    """A prompt template is empty or has no checksum."""

    code = "INVALID_PROMPT_TEMPLATE"


class LlmProviderFailed(ServiceUnavailableError):
    """The configured model provider failed after bounded retries; never fall back to the echo."""

    code = "LLM_PROVIDER_FAILED"


class UnknownLastEventId(ValidationFailedError):
    """The supplied Last-Event-ID is unknown or belongs to another run."""

    code = "UNKNOWN_LAST_EVENT_ID"
    status_code = 400
