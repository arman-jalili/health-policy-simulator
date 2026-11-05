"""FastAPI dependencies of the EvidenceCorpus interface layer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request

from evidence_corpus.composition import CorpusContainer


def get_container(request: Request) -> CorpusContainer:
    """Return the wired corpus container of the running application."""
    return cast(CorpusContainer, request.app.state.corpus)


async def corpus_unit_of_work(request: Request) -> AsyncIterator[None]:
    """One transaction per corpus request: aggregate writes and outbox rows commit together."""
    container = get_container(request)
    async with container.transaction():
        yield
