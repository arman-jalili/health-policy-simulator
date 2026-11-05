"""Fail-closed figure lookup until ClaimValidation exposes a synchronous read port."""

from __future__ import annotations

from governance_compliance.application.values import FigureVerdict


class UnknownFigureVerdicts:
    async def verdict_for(self, reference_figure_id: str) -> FigureVerdict | None:
        return None
