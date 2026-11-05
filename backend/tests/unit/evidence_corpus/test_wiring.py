"""Wiring contract: the running app must expose real adapters (issue #26).

Canonical: `.pi/architecture/modules/evidence-corpus.md` — Wiring Contract

These tests are deliberately about composition, not behaviour: a use case that only works when it
is instantiated by hand is not wired. The integration suite proves the PostgreSQL round-trip.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from evidence_corpus.composition import build_container
from evidence_corpus.infrastructure.events import OutboxEventPublisher
from evidence_corpus.infrastructure.indexing.memory import InMemoryIndexWriter
from evidence_corpus.infrastructure.indexing.postgres import PostgresIndexWriter
from evidence_corpus.infrastructure.logging_events import LoggingEventPublisher
from evidence_corpus.infrastructure.memory import (
    InMemoryArticleRepository,
    InMemoryAuthorityRuleRepository,
    InMemoryCorpusSnapshotRepository,
    InMemoryDocumentRepository,
    InMemoryIngestionRunRepository,
    InMemoryPassageRepository,
)
from evidence_corpus.infrastructure.repository.sqlalchemy import (
    SqlAlchemyArticleRepository,
    SqlAlchemyAuthorityRuleRepository,
    SqlAlchemyCorpusSnapshotRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionRunRepository,
    SqlAlchemyPassageRepository,
)
from shared.app import create_app
from shared.config import Settings
from shared.db import Database
from shared.enums import Persistence
from shared.errors import (
    STATUS_CODE_TO_ERROR,
    AppError,
    BadRequestError,
    ForbiddenError,
    RateLimitedError,
    UnauthorizedError,
)

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"
SRC = Path(__file__).resolve().parents[3] / "src"

DOCUMENT_ROUTES = {
    "/api/v1/corpus/documents",
    "/api/v1/corpus/ingestion-runs",
    "/api/v1/corpus/ingestion-runs/{run_id}",
    "/api/v1/documents/{document_id}",
    "/api/v1/passages/{passage_id}",
    "/api/v1/corpus/snapshots",
    "/api/v1/corpus/snapshots/{snapshot_id}",
    "/api/v1/corpus/authority-rules",
}


def memory_settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        persistence=Persistence.MEMORY,
    )


def postgres_settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        persistence=Persistence.POSTGRES,
    )


def test_memory_container_uses_only_in_memory_adapters() -> None:
    container = build_container(memory_settings())

    assert isinstance(container.documents, InMemoryDocumentRepository)
    assert isinstance(container.articles, InMemoryArticleRepository)
    assert isinstance(container.passages, InMemoryPassageRepository)
    assert isinstance(container.ingestion_runs, InMemoryIngestionRunRepository)
    assert isinstance(container.snapshots, InMemoryCorpusSnapshotRepository)
    assert isinstance(container.authority_rules, InMemoryAuthorityRuleRepository)
    assert isinstance(container.events, LoggingEventPublisher)
    assert isinstance(container.index_writer, InMemoryIndexWriter)
    assert container.unit_of_work is None


def test_postgres_container_uses_only_sqlalchemy_adapters() -> None:
    database = Database(postgres_settings())
    try:
        container = build_container(postgres_settings(), database)
    finally:
        asyncio.run(database.dispose())

    assert isinstance(container.documents, SqlAlchemyDocumentRepository)
    assert isinstance(container.articles, SqlAlchemyArticleRepository)
    assert isinstance(container.passages, SqlAlchemyPassageRepository)
    assert isinstance(container.ingestion_runs, SqlAlchemyIngestionRunRepository)
    assert isinstance(container.snapshots, SqlAlchemyCorpusSnapshotRepository)
    assert isinstance(container.authority_rules, SqlAlchemyAuthorityRuleRepository)
    assert isinstance(container.events, OutboxEventPublisher)
    assert isinstance(container.index_writer, PostgresIndexWriter)
    assert container.unit_of_work is not None


def test_postgres_without_a_database_is_refused() -> None:
    with pytest.raises(ValueError, match="PERSISTENCE=postgres"):
        build_container(postgres_settings())


def test_app_registers_every_corpus_route() -> None:
    app = create_app(memory_settings())

    paths = set(app.openapi()["paths"])

    assert paths >= DOCUMENT_ROUTES


def test_app_exposes_the_configured_container() -> None:
    app = create_app(memory_settings())

    assert isinstance(app.state.corpus.documents, InMemoryDocumentRepository)


def test_router_contains_no_residue_of_the_frozen_stub() -> None:
    source = (SRC / "evidence_corpus/interfaces/http/router.py").read_text()
    composition = (SRC / "evidence_corpus/composition.py").read_text()

    assert "_not_implemented" not in source
    assert "not wired yet" not in source
    assert "_not_implemented" not in composition


# These four are constructed only by the HTTP-status translation layer in shared/http/errors.py,
# from a Starlette HTTPException. They have no literal `raise` site of their own.
_STATUS_TRANSLATED_ERRORS = {
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    RateLimitedError,
}


def _app_error_taxonomy() -> list[type[AppError]]:
    found: list[type[AppError]] = []
    pending: list[type[AppError]] = [AppError]
    while pending:
        current = pending.pop()
        for child in current.__subclasses__():
            if child not in found:
                found.append(child)
                pending.append(child)
    return found


def test_no_app_error_subclass_is_an_unraisable_orphan() -> None:
    """A class that nothing raises is residue, not a contract (issue #28)."""
    # The definition file and the OpenAPI re-export file are exactly where dead classes hide:
    # being named there proves nothing about reachability.
    sources = [
        path.read_text()
        for path in SRC.rglob("*.py")
        if path not in {SRC / "shared/errors.py", SRC / "shared/http/schemas.py"}
    ]

    orphans = [
        cls.__name__
        for cls in _app_error_taxonomy()
        if cls.__module__ == "shared.errors"
        and cls not in _STATUS_TRANSLATED_ERRORS
        and not any(cls.__name__ in source for source in sources)
    ]

    assert orphans == []
    assert set(STATUS_CODE_TO_ERROR.values()) >= _STATUS_TRANSLATED_ERRORS
    assert 501 not in STATUS_CODE_TO_ERROR


def test_domain_layer_never_imports_infrastructure() -> None:
    offenders = []
    for path in (SRC / "evidence_corpus/domain").rglob("*.py"):
        source = path.read_text()
        if "evidence_corpus.infrastructure" in source or "import sqlalchemy" in source:
            offenders.append(str(path.relative_to(SRC)))

    assert offenders == []
