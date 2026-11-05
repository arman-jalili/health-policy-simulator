"""Static model price table (issue #208).

Canonical: .pi/architecture/decisions/ADR-006-cost-tracking.md

A model without a price is a boot/invocation error, never a silent zero. The real settings-backed
table is wired in issue #216.
"""

from __future__ import annotations

from collections.abc import Mapping

from simulation_orchestration.application.errors import UnknownModel
from simulation_orchestration.application.values import ModelPrice


class StaticPriceTable:
    def __init__(self, prices: Mapping[str, ModelPrice]) -> None:
        self._prices = dict(prices)

    def price_for(self, model_id: str) -> ModelPrice:
        price = self._prices.get(model_id)
        if price is None:
            raise UnknownModel(f"no price entry for model {model_id!r}")
        return price
