"""FastAPI dependencies of the EvidenceCorpus interface layer."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from evidence_corpus.composition import CorpusContainer


def get_container(request: Request) -> CorpusContainer:
    """Return the wired corpus container of the running application."""
    return cast(CorpusContainer, request.app.state.corpus)
