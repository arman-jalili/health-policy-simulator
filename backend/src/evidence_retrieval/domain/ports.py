"""Ports required by domain services (dependency inversion inside the domain).

Canonical: .pi/architecture/modules/evidence-retrieval.md

The LLM-assisted stance model is a vendor capability, but the domain service owns validation and
the strategy boundary. This protocol keeps ``domain/`` free of infrastructure imports.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from evidence_corpus.domain.published import PassageView
from evidence_retrieval.domain.values import StanceLabel


@runtime_checkable
class StanceModelPort(Protocol):
    """Model-assisted stance proposal; the domain service validates the label."""

    async def classify(self, claim: str, passage: PassageView) -> StanceLabel: ...
