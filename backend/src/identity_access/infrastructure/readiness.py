"""Readiness adapters for the identity-access context (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

``/readyz`` in the shared shell performs the full DB + LLM checks. The container still exposes the
frozen ``ReadinessPort`` so a later composition can delegate to it without changing the contract.
"""

from __future__ import annotations

import asyncio

from identity_access.interfaces.dto import ReadinessCheck, ReadinessReport
from shared.db import Database
from shared.log_setup import get_logger

logger = get_logger(__name__)


class DatabaseReadiness:
    """Report database reachability via a bounded ping."""

    def __init__(self, database: Database, timeout_s: float) -> None:
        self._database = database
        self._timeout_s = timeout_s

    async def check(self) -> ReadinessReport:
        try:
            async with asyncio.timeout(self._timeout_s):
                await self._database.ping()
        except Exception as error:
            logger.warning("readiness_check_failed", check="database", error=str(error))
            return ReadinessReport(
                ready=False,
                checks=(ReadinessCheck(name="database", ok=False, detail="unreachable"),),
            )
        return ReadinessReport(
            ready=True,
            checks=(ReadinessCheck(name="database", ok=True),),
        )


class AlwaysReadyReadiness:
    """Memory mode has no external dependency to probe."""

    async def check(self) -> ReadinessReport:
        return ReadinessReport(ready=True, checks=())
