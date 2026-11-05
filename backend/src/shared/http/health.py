"""Liveness and readiness probes.

``/healthz`` is process liveness only — it must stay answerable while the database is down, so a
restart loop never hides a dependency outage. ``/readyz`` checks database connectivity and returns
``503`` with the standard envelope when the dependency is unavailable.

Canonical: .pi/architecture/implementation-roadmap.md (Phase 0 acceptance criteria)
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shared.errors import ErrorDetail, ServiceUnavailableError
from shared.http.deps import get_app_settings, get_database
from shared.log_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
async def healthz(request: Request) -> dict[str, str]:
    settings = get_app_settings(request)
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.version,
    }


@router.get(
    "/readyz",
    summary="Readiness probe",
    responses={503: {"description": "A required dependency is unavailable"}},
)
async def readyz(request: Request) -> JSONResponse:
    settings = get_app_settings(request)
    database = get_database(request)

    try:
        async with asyncio.timeout(settings.db_connect_timeout_s):
            await database.ping()
    except Exception as error:
        logger.warning("readiness_check_failed", check="database", error=str(error))
        raise ServiceUnavailableError(
            "Database is not reachable",
            code="NOT_READY",
            details=[
                ErrorDetail(
                    message="connectivity check failed",
                    field="database",
                    code="unavailable",
                )
            ],
        ) from error

    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "service": settings.service_name,
            "checks": {"database": "ok"},
        },
        headers={"Cache-Control": "no-store"},
    )
