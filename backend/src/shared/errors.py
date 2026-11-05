"""Application error hierarchy and the uniform error envelope (ADR-004).

Every failure that leaves the process is rendered as::

    {"code": "VALIDATION_FAILED", "message": "...", "details": [...], "trace_id": "..."}

``code`` is a stable machine-readable identifier; clients branch on it, never on ``message``.
Domain-specific errors (``AuthorityClaimRejected``, ``PositionRevisionRejected``, ...) subclass
:class:`ConflictError` / :class:`AppError` inside their own bounded context and pass their code.

Canonical: .pi/architecture/decisions/ADR-004-api-design.md
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(slots=True)
class ErrorDetail:
    """A single machine-readable reason attached to an error."""

    message: str
    field: str | None = None
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        detail: dict[str, Any] = {"message": self.message}
        if self.field is not None:
            detail["field"] = self.field
        if self.code is not None:
            detail["code"] = self.code
        return detail


@dataclass(slots=True)
class ErrorEnvelope:
    """Wire representation of an error response body."""

    code: str
    message: str
    trace_id: str
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "trace_id": self.trace_id,
        }


class AppError(Exception):
    """Base class for expected, client-visible failures."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    default_message: ClassVar[str] = "Unexpected error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Sequence[ErrorDetail | dict[str, Any]] | None = None,
    ) -> None:
        self.message = message or self.default_message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = [self._as_detail(item) for item in (details or [])]
        super().__init__(self.message)

    @staticmethod
    def _as_detail(item: ErrorDetail | dict[str, Any]) -> ErrorDetail:
        if isinstance(item, ErrorDetail):
            return item
        return ErrorDetail(
            message=str(item.get("message", "")),
            field=item.get("field"),
            code=item.get("code"),
        )

    def envelope(self, trace_id: str) -> ErrorEnvelope:
        return ErrorEnvelope(
            code=self.code,
            message=self.message,
            trace_id=trace_id,
            details=[detail.to_dict() for detail in self.details],
        )

    def to_response_body(self, trace_id: str) -> dict[str, Any]:
        return self.envelope(trace_id).to_dict()


class ValidationFailedError(AppError):
    code = "VALIDATION_FAILED"
    status_code = 422
    default_message = "Request validation failed"


class BadRequestError(AppError):
    code = "BAD_REQUEST"
    status_code = 400
    default_message = "Malformed request"


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
    default_message = "Resource not found"


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409
    default_message = "Request conflicts with current state"


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = 401
    default_message = "Authentication required"


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = 403
    default_message = "Insufficient scope for this operation"


class RateLimitedError(AppError):
    code = "RATE_LIMITED"
    status_code = 429
    default_message = "Too many requests"


class ServiceUnavailableError(AppError):
    code = "SERVICE_UNAVAILABLE"
    status_code = 503
    default_message = "Dependency unavailable"


class InternalError(AppError):
    code = "INTERNAL_ERROR"
    status_code = 500
    default_message = "Unexpected error"


STATUS_CODE_TO_ERROR: dict[int, type[AppError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationFailedError,
    429: RateLimitedError,
    503: ServiceUnavailableError,
    500: InternalError,
}
