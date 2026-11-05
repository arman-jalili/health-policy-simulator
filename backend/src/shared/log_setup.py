"""Structured JSON logging with request context and secret redaction (ADR-004, ADR-005).

Every log line carries ``trace_id``/``request_id`` bound by the request middleware. Fields whose
name suggests a credential are redacted before rendering, so API keys cannot leak into logs.

Canonical: .pi/architecture/decisions/ADR-004-api-design.md (error envelope, trace id)
"""

from __future__ import annotations

import logging as stdlib_logging
import sys
from collections.abc import MutableMapping
from typing import Any, TextIO, cast

import structlog
from structlog.typing import EventDict, FilteringBoundLogger, WrappedLogger

from shared.config import Settings
from shared.enums import LogFormat

SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "database_url",
        "password",
        "secret",
        "token",
        "x-api-key",
    }
)
REDACTED = "***"

_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error")
# uvicorn logs access lines whenever its logger has handlers; our middleware already emits
# one structured access line with trace context, so the duplicate is switched off here.
UVICORN_ACCESS_LOGGER = "uvicorn.access"


def _redact_value(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return value
    if isinstance(value, MutableMapping):
        return {
            key: (
                REDACTED if str(key).lower() in SENSITIVE_KEYS else _redact_value(item, depth + 1)
            )
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact_value(item, depth + 1) for item in value]
    return value


def redact_secrets(_logger: WrappedLogger, _name: str, event_dict: EventDict) -> EventDict:
    """structlog processor that masks credential-shaped fields."""
    for key in list(event_dict):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = REDACTED
        else:
            event_dict[key] = _redact_value(event_dict[key])
    return event_dict


def configure_logging(settings: Settings, stream: TextIO | None = None) -> None:
    """Install one JSON handler on the root logger and route structlog through it."""
    output = stream or sys.stdout
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer(sort_keys=True)
        if settings.log_format is LogFormat.JSON
        else structlog.dev.ConsoleRenderer()
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        redact_secrets,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.ExceptionRenderer(),
            renderer,
        ],
    )
    handler = stdlib_logging.StreamHandler(output)
    handler.setFormatter(formatter)

    root = stdlib_logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    for name in _UVICORN_LOGGERS:
        logger = stdlib_logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    access_logger = stdlib_logging.getLogger(UVICORN_ACCESS_LOGGER)
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(stdlib_logging, settings.log_level)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """Return a bound logger carrying the current request context."""
    return cast(FilteringBoundLogger, structlog.get_logger(name))
