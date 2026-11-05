"""Uniform error rendering for every failure mode (ADR-004).

All paths converge on ``{"code", "message", "details", "trace_id"}``. Unexpected exceptions are
logged with their traceback and returned as a generic 500 — internal detail never reaches the
client, but the trace id lets an operator find the log line.

Canonical: .pi/architecture/decisions/ADR-004-api-design.md
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.errors import STATUS_CODE_TO_ERROR, AppError, ErrorDetail, ErrorEnvelope, InternalError
from shared.http.middleware import REQUEST_ID_HEADER, TRACE_ID_HEADER
from shared.ids import new_id
from shared.log_setup import get_logger

logger = get_logger(__name__)
REQUEST_ID_PREFIX = "req"


def _trace_id(request: Request) -> str:
    bound = getattr(request.state, "trace_id", None)
    return bound if isinstance(bound, str) and bound else new_id(REQUEST_ID_PREFIX)


def _response(
    request: Request,
    envelope: ErrorEnvelope,
    status_code: int,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    response_headers = {
        REQUEST_ID_HEADER: envelope.trace_id,
        TRACE_ID_HEADER: envelope.trace_id,
    }
    if headers:
        response_headers.update(headers)
    return JSONResponse(
        status_code=status_code,
        content=envelope.to_dict(),
        headers=response_headers,
    )


async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    """Render an expected application failure."""
    if not isinstance(exc, AppError):  # pragma: no cover - defensive, FastAPI guarantees type
        return await handle_unexpected_error(request, exc)

    trace_id = _trace_id(request)
    log = logger.error if exc.status_code >= 500 else logger.warning
    log(
        "request_rejected",
        error_code=exc.code,
        status_code=exc.status_code,
        detail_count=len(exc.details),
    )
    headers = {"Retry-After": "5"} if exc.status_code == 503 else None
    return _response(request, exc.envelope(trace_id), exc.status_code, headers)


async def handle_request_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Translate Pydantic validation failures into the error envelope."""
    if not isinstance(exc, RequestValidationError):  # pragma: no cover - defensive
        return await handle_unexpected_error(request, exc)

    details = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part not in ("body", "query")]
        details.append(
            ErrorDetail(
                message=str(error.get("msg", "invalid value")),
                field=".".join(location) or None,
                code=str(error.get("type", "invalid")),
            )
        )
    failure = AppError(
        "Request validation failed",
        code="VALIDATION_FAILED",
        status_code=422,
        details=details,
    )
    trace_id = _trace_id(request)
    logger.warning("request_rejected", error_code=failure.code, detail_count=len(details))
    return _response(request, failure.envelope(trace_id), failure.status_code)


async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    """Map Starlette/FastAPI ``HTTPException`` onto a stable machine code."""
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover - defensive
        return await handle_unexpected_error(request, exc)

    error_type = STATUS_CODE_TO_ERROR.get(exc.status_code)
    message = exc.detail if isinstance(exc.detail, str) and exc.detail else None
    if error_type is not None:
        failure = error_type(message)
    else:
        failure = AppError(
            message or "Request failed",
            code=f"HTTP_{exc.status_code}",
            status_code=exc.status_code,
        )

    trace_id = _trace_id(request)
    logger.warning("request_rejected", error_code=failure.code, status_code=exc.status_code)
    headers = dict(exc.headers) if exc.headers else None
    return _response(request, failure.envelope(trace_id), exc.status_code, headers)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Log the traceback and hide internals behind a generic envelope."""
    trace_id = _trace_id(request)
    logger.error(
        "request_failed",
        error_type=type(exc).__name__,
        error_message=str(exc),
        exc_info=exc,
    )
    failure: AppError = InternalError()
    return _response(request, failure.envelope(trace_id), failure.status_code)


def register_error_handlers(app: FastAPI) -> None:
    """Attach the handlers above to an application instance."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)


__all__ = [
    "ErrorEnvelope",
    "handle_app_error",
    "handle_http_exception",
    "handle_request_validation_error",
    "handle_unexpected_error",
    "register_error_handlers",
]
