"""Composition root of the modular monolith (ADR-001) — application shell, not kernel code.

Contexts are added to :func:`create_app` as they are built; at bootstrap only the shared kernel
and the health probes exist. Run with ``uvicorn shared.app:create_app --factory`` or ``hps-api``.

Canonical: .pi/architecture/decisions/ADR-001-architecture-pattern.md
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from evidence_corpus.interfaces.http.router import router as evidence_corpus_router
from shared.config import Settings, get_settings
from shared.db import Database
from shared.http.errors import register_error_handlers
from shared.http.health import router as health_router
from shared.http.middleware import RequestContextMiddleware
from shared.log_setup import configure_logging, get_logger

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI application. Configuration errors abort here, before serving."""
    app_settings = settings or get_settings()
    configure_logging(app_settings)
    database = Database(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "service_starting",
            env=str(app_settings.env),
            auth_mode=str(app_settings.auth_mode),
            version=app_settings.version,
        )
        if app_settings.is_demo:
            logger.warning(
                "demo_auth_mode_enabled",
                detail="anonymous reads and runs:write are allowed from localhost only",
            )
        try:
            await database.ping()
        except Exception as error:
            logger.warning("database_unreachable_at_startup", error=str(error))
        try:
            yield
        finally:
            await database.dispose()
            logger.info("service_stopped")

    app = FastAPI(
        title=app_settings.service_name,
        version=app_settings.version,
        summary="Institutional negotiation simulator for Austrian healthcare policy",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.db = database

    if app_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key", "X-Request-ID"],
            expose_headers=["X-Request-ID", "X-Trace-Id"],
        )

    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(evidence_corpus_router)
    return app


def main() -> None:
    """Console entrypoint (``hps-api``)."""
    settings = get_settings()
    uvicorn.run(
        "shared.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":  # pragma: no cover - process entry
    main()
