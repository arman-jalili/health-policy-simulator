"""Logging contract: JSON output, redacted credentials, request context propagation."""

from __future__ import annotations

import json
from io import StringIO
from typing import Any, cast

import structlog

from shared.config import Settings
from shared.log_setup import REDACTED, configure_logging, get_logger, redact_secrets


def test_redaction_masks_top_level_and_nested_secrets() -> None:
    event: dict[str, Any] = {
        "api_key": "secret-value",
        "X-API-Key": "secret-value",
        "nested": {"password": "secret-value", "safe": "visible"},
        "safe": "visible",
    }

    result = redact_secrets(cast(Any, None), "info", event)

    assert result["api_key"] == REDACTED
    assert result["X-API-Key"] == REDACTED
    assert cast(dict[str, Any], result["nested"])["password"] == REDACTED
    assert result["safe"] == "visible"
    assert cast(dict[str, Any], result["nested"])["safe"] == "visible"


def test_json_logging_emits_one_object_per_line() -> None:
    stream = StringIO()
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://hps:hps@localhost:5433/health_policy",
    )
    configure_logging(settings, stream=stream)
    structlog.contextvars.bind_contextvars(trace_id="req_01J0000000000000000000000F")

    try:
        get_logger("test").info("something_happened", api_key="should-not-leak", count=2)
    finally:
        structlog.contextvars.clear_contextvars()

    payload = json.loads(stream.getvalue().strip())
    assert payload["event"] == "something_happened"
    assert payload["level"] == "info"
    assert payload["trace_id"] == "req_01J0000000000000000000000F"
    assert payload["count"] == 2
    assert payload["api_key"] == REDACTED
    assert "should-not-leak" not in stream.getvalue()


def test_uvicorn_access_logger_is_silenced_to_avoid_duplicate_access_lines() -> None:
    import logging

    configure_logging(
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://hps:hps@localhost:5433/health_policy",
        ),
        stream=StringIO(),
    )

    access_logger = logging.getLogger("uvicorn.access")
    assert access_logger.disabled
    assert not access_logger.hasHandlers()
