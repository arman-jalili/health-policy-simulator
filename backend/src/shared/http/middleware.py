"""Request identity, access logging and trace propagation (ADR-004).

The middleware accepts a caller-supplied ``X-Request-ID`` when it looks like a trace id and
generates one otherwise, binds it to the logging context, and echoes it on the response. The
same value is returned as ``trace_id`` in every error envelope.

Canonical: .pi/architecture/decisions/ADR-004-api-design.md
"""

from __future__ import annotations

import re
from time import perf_counter

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from shared.ids import new_id
from shared.log_setup import get_logger

REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-Id"
REQUEST_ID_PREFIX = "req"
_TRACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")

logger = get_logger(__name__)


def _resolve_trace_id(request: Request) -> str:
    candidate = request.headers.get(REQUEST_ID_HEADER, "").strip()
    if candidate and _TRACE_ID_PATTERN.match(candidate):
        return candidate
    return new_id(REQUEST_ID_PREFIX)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind trace id plus request metadata and emit one access log line per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = _resolve_trace_id(request)
        request.state.trace_id = trace_id

        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            request_id=trace_id,
            method=request.method,
            path=request.url.path,
        )
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "http_request_failed",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
            raise
        else:
            duration_ms = round((perf_counter() - started) * 1000, 2)
            response.headers[REQUEST_ID_HEADER] = trace_id
            response.headers[TRACE_ID_HEADER] = trace_id
            logger.info(
                "http_request",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()
