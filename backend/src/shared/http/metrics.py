"""Metrics exposition endpoint (Prometheus text format)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from shared.metrics import METRICS

router = APIRouter(tags=["observability"])


@router.get("/metrics", summary="Process metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(METRICS.render(), media_type="text/plain; version=0.0.4")
