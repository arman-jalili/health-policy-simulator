"""Composition root of the modular monolith (ADR-001) — application shell, not kernel code.

Every context is wired here for the configured persistence family; the in-process outbox relay
runs for PostgreSQL mode. Run with ``uvicorn shared.app:create_app --factory`` or ``hps-api``.

Canonical: .pi/architecture/decisions/ADR-001-architecture-pattern.md
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from claim_validation.composition import build_container as build_claim_validation_container
from claim_validation.interfaces.http.router import router as claim_validation_router
from evidence_corpus.composition import build_container
from evidence_corpus.interfaces.http.router import router as evidence_corpus_router
from evidence_retrieval.composition import build_container as build_retrieval_container
from evidence_retrieval.interfaces.http.router import router as evidence_retrieval_router
from identity_access.composition import build_identity_access_container
from identity_access.interfaces.http.router import router as identity_access_router
from shared.config import Settings, get_settings
from shared.db import Database
from shared.enums import Persistence
from shared.http.errors import register_error_handlers
from shared.http.health import router as health_router
from shared.http.metrics import router as metrics_router
from shared.http.middleware import RequestContextMiddleware
from shared.log_setup import configure_logging, get_logger
from shared.outbox import OutboxEvent
from shared.relay import WILDCARD, OutboxRelay
from simulation_orchestration.composition import build_container as build_simulation_container
from simulation_orchestration.interfaces.http.router import (
    router as simulation_orchestration_router,
)
from stakeholder_model.composition import build_container as build_stakeholder_container
from stakeholder_model.interfaces.http.router import router as stakeholder_model_router

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI application. Configuration errors abort here, before serving."""
    app_settings = settings or get_settings()
    configure_logging(app_settings)
    database = Database(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        relay_task: asyncio.Task[None] | None = None
        worker_task: asyncio.Task[None] | None = None
        worker_stop = asyncio.Event()
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
        if app_settings.persistence is Persistence.POSTGRES:
            relay = OutboxRelay(database.session_factory, poll_interval_s=5.0)
            relay.subscribe(WILDCARD, _log_dispatched_event)
            relay_task = asyncio.create_task(relay.run(), name="outbox-relay")
        worker_task = asyncio.create_task(
            app.state.simulation_orchestration.worker.run_forever(worker_stop),
            name="simulation-worker",
        )
        try:
            yield
        finally:
            worker_stop.set()
            if worker_task is not None:
                with suppress(asyncio.CancelledError, TimeoutError):
                    await asyncio.wait_for(worker_task, timeout=2.0)
            if relay_task is not None:
                relay_task.cancel()
                with suppress(asyncio.CancelledError):
                    await relay_task
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
    app.state.corpus = build_container(app_settings, database)
    app.state.evidence_retrieval = build_retrieval_container(
        app_settings, database, corpus=app.state.corpus
    )
    app.state.identity_access = build_identity_access_container(app_settings, database)
    app.state.stakeholder_model = build_stakeholder_container(app_settings, database)
    app.state.claim_validation = build_claim_validation_container(app_settings, database)
    app.state.simulation_orchestration = build_simulation_container(app_settings, database)

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
    app.include_router(metrics_router)
    app.include_router(evidence_corpus_router)
    app.include_router(evidence_retrieval_router)
    app.include_router(identity_access_router)
    app.include_router(stakeholder_model_router)
    app.include_router(claim_validation_router)
    app.include_router(simulation_orchestration_router)
    return app


async def _log_dispatched_event(event: OutboxEvent) -> None:
    """Phase 1 in-process subscriber: make relayed events observable until consumers exist."""
    logger.info(
        "domain_event_dispatched",
        event_name=event.event_name,
        event_id=event.event_id,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
    )


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
