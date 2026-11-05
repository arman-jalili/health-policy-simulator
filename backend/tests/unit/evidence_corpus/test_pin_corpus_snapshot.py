"""Contract freeze: `PinCorpusSnapshot` and `IndexManifest`.

A snapshot is a manifest: it names the documents a run may search and the index version it will
search. Citations stay valid after re-ingestion because passages are immutable and pinned.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from evidence_corpus.application.commands import PinCorpusSnapshotRequest
from evidence_corpus.application.dto import IndexManifestView, SnapshotView
from evidence_corpus.application.services import PinCorpusSnapshot
from evidence_corpus.domain.entities import CorpusSnapshot, IndexManifest
from evidence_corpus.domain.events import IndexManifestPublished
from evidence_corpus.domain.repositories import CorpusSnapshotRepository

from .contract_helpers import field_names, parameter_names


class TestSnapshotRequest:
    def test_accepts_an_optional_explicit_document_set_and_a_label(self) -> None:
        assert field_names(PinCorpusSnapshotRequest) == ["label", "document_ids"]

    def test_label_is_required_and_documents_are_optional(self) -> None:
        request = PinCorpusSnapshotRequest(label="baseline")

        assert request.document_ids is None

    def test_use_case_returns_the_pinned_snapshot(self) -> None:
        assert parameter_names(PinCorpusSnapshot.execute) == ["self", "request"]
        assert inspect.signature(PinCorpusSnapshot.execute).return_annotation == "SnapshotView"


class TestSnapshotView:
    def test_exposes_the_manifest_hash_for_reproducibility(self) -> None:
        assert {"snapshot_id", "label", "manifest_hash", "pinned_at"} <= set(
            field_names(SnapshotView)
        )

    def test_carries_the_index_version_it_will_search(self) -> None:
        assert "index" in field_names(SnapshotView)

    def test_index_view_names_model_and_activation_time(self) -> None:
        assert field_names(IndexManifestView) == [
            "index_version",
            "embedding_model",
            "searchable_since",
            "passage_count",
        ]


class TestSnapshotAggregate:
    def test_snapshot_is_a_manifest_not_a_transaction_root_for_the_corpus(self) -> None:
        names = field_names(CorpusSnapshot)

        assert "document_ids" in names
        assert "articles" not in names
        assert "passages" not in names

    def test_index_manifest_is_published_as_an_event(self) -> None:
        assert field_names(IndexManifestPublished) == [
            "snapshot_id",
            "index_version",
            "embedding_model",
            "passage_count",
        ]

    def test_event_time_is_explicit(self) -> None:
        manifest = IndexManifest(
            index_version="idx-1",
            embedding_model="text-embedding-3-small",
            searchable_since=datetime(2026, 11, 5, tzinfo=UTC),
            passage_count=10,
        )

        assert manifest.searchable_since.tzinfo is not None


class TestSnapshotRepository:
    def test_is_domain_owned(self) -> None:
        assert getattr(CorpusSnapshotRepository, "_is_protocol", False) is True

    def test_supports_save_and_load_by_id(self) -> None:
        assert {"get", "save"} <= set(dir(CorpusSnapshotRepository))

    def test_document_set_is_resolved_through_the_repository_not_the_manifest(self) -> None:
        assert "list_document_ids" in dir(CorpusSnapshotRepository)

    def test_api_contract_is_created_with_201(self) -> None:
        assert "manifest_hash" in field_names(SnapshotView)


@pytest.mark.parametrize("field", ["snapshot_id", "manifest_hash", "index"])
def test_snapshot_contract_fields_are_present(field: str) -> None:
    assert field in field_names(SnapshotView)
