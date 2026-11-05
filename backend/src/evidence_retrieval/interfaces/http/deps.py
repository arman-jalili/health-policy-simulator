"""FastAPI dependencies of the EvidenceRetrieval interface layer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request

from evidence_retrieval.composition import EvidenceRetrievalContainer


def get_container(request: Request) -> EvidenceRetrievalContainer:
    """Return the wired retrieval container of the running application."""
    return cast(EvidenceRetrievalContainer, request.app.state.evidence_retrieval)


async def evidence_retrieval_unit_of_work(request: Request) -> AsyncIterator[None]:
    """One transaction per retrieval request: pack, candidates and outbox commit together."""
    container = get_container(request)
    async with container.transaction():
        yield
