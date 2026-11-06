"""Liveness and readiness probes.

``/healthz`` is process liveness only — it must stay answerable while the database is down, so a
restart loop never hides a dependency outage. ``/readyz`` checks database connectivity and, when
configured, LLM reachability; it returns ``503`` with the standard envelope when any required
dependency is unavailable.

Canonical: .pi/architecture/implementation-roadmap.md (Phase 0 acceptance criteria)
"""

from __future__ import annotations

import asyncio

import httpx
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


async def _check_llm(health_url: str | None, timeout_s: float) -> tuple[bool, str]:
    """Return ``(ok, status)``; an unset URL is reported as not configured, not a failure."""
    if not health_url:
        return True, "not_configured"
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(health_url)
    except Exception as error:
        logger.warning("readiness_check_failed", check="llm", error=str(error))
        return False, "unreachable"
    if response.is_success:
        return True, "ok"
    return False, f"http_{response.status_code}"


@router.get(
    "/readyz",
    summary="Readiness probe",
    responses={503: {"description": "A required dependency is unavailable"}},
)
async def readyz(request: Request) -> JSONResponse:
    settings = get_app_settings(request)
    database = get_database(request)
    checks: dict[str, str] = {}
    failures: list[ErrorDetail] = []

    try:
        async with asyncio.timeout(settings.db_connect_timeout_s):
            await database.ping()
        checks["database"] = "ok"
    except Exception as error:
        logger.warning("readiness_check_failed", check="database", error=str(error))
        checks["database"] = "unreachable"
        failures.append(
            ErrorDetail(
                message="connectivity check failed",
                field="database",
                code="unavailable",
            )
        )

    llm_ok, llm_status = await _check_llm(settings.llm_health_url, settings.db_connect_timeout_s)
    checks["llm"] = llm_status
    if not llm_ok:
        failures.append(
            ErrorDetail(
                message="LLM health check failed",
                field="llm",
                code=llm_status,
            )
        )

    retrieval = getattr(request.app.state, "evidence_retrieval", None)
    if retrieval is not None:
        readiness = await retrieval.readiness.check()
        retrieval_ok = readiness.embeddings_reachable and readiness.reranker_reachable
        checks["evidence_retrieval"] = "ok" if retrieval_ok else "unreachable"
        checks["evidence_retrieval_mode"] = readiness.mode
        if readiness.detail is not None:
            checks["evidence_retrieval_detail"] = readiness.detail
        if not retrieval_ok:
            failures.append(
                ErrorDetail(
                    message=readiness.detail or "retrieval dependency unreachable",
                    field="evidence_retrieval",
                    code="unavailable",
                )
            )

    decision_brief = getattr(request.app.state, "decision_brief", None)
    if decision_brief is not None:
        unwired = decision_brief.unwired_gates()
        # Fail-closed gates are a deliberate state, not an outage: publication refuses rather than
        # skips a gate, so readiness reports the state without failing the probe (D-007).
        checks["decision_brief"] = "degraded" if unwired else "ok"
        checks["decision_brief_gates"] = ",".join(unwired) if unwired else "wired"

    stakeholder = getattr(request.app.state, "stakeholder_model", None)
    if stakeholder is not None:
        institution_count = len(stakeholder.allowlist.institutions)
        checks["stakeholder_model"] = "ok" if institution_count == 9 else "degraded"
        checks["stakeholder_institutions"] = str(institution_count)

    consensus = getattr(request.app.state, "consensus_analysis", None)
    if consensus is not None:
        # Derived projections are always "ok" as a store; the inputs are what can be missing, and a
        # missing input is a named refusal on the derivation path rather than a broken probe.
        checks["consensus_analysis"] = "ok"
        checks["consensus_analysis_projection"] = str(settings.persistence)

    claims = getattr(request.app.state, "claim_validation", None)
    if claims is not None:
        checks["claim_validation"] = "ok"
        checks["claim_validation_persistence"] = str(settings.persistence)

    simulation = getattr(request.app.state, "simulation_orchestration", None)
    if simulation is not None:
        worker_task = getattr(request.app.state, "simulation_worker_task", None)
        worker_alive = worker_task is not None and not worker_task.done()
        checks["simulation_orchestration"] = "ok"
        checks["simulation_orchestration_persistence"] = str(settings.persistence)
        checks["simulation_model"] = settings.simulation_model_id
        configured = (
            settings.simulation_input_price_per_1k > 0
            or settings.simulation_output_price_per_1k > 0
        )
        checks["simulation_pricing"] = "configured" if configured else "zero"
        checks["simulation_worker"] = (
            "not_started" if worker_task is None else ("ok" if worker_alive else "dead")
        )
        if worker_task is not None and not worker_alive:
            failures.append(
                ErrorDetail(
                    message="simulation worker task is not running",
                    field="simulation_worker",
                    code="dead",
                )
            )

    governance = getattr(request.app.state, "governance_compliance", None)
    if governance is not None:
        checks["governance_compliance"] = "ok"
        checks["governance_allowlist"] = str(len(governance.allowlist.institutions))
        checks["governance_provenance"] = "deferred"

    if failures:
        raise ServiceUnavailableError(
            "A required dependency is unavailable",
            code="NOT_READY",
            details=failures,
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "service": settings.service_name,
            "checks": checks,
        },
        headers={"Cache-Control": "no-store"},
    )
