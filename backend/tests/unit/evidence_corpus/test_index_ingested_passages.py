"""Contract freeze: `IndexIngestedPassages`.

Indexing is a write contract with two obligations: passages become searchable in the same run, and
re-running is idempotent. Withdrawal is explicit (`PassageRevertedFromIndex`) so no later argument
can cite a retracted passage.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from evidence_corpus.application.commands import IndexIngestedPassagesRequest
from evidence_corpus.application.dto import IndexManifestView
from evidence_corpus.application.ports import IndexWriterPort
from evidence_corpus.application.services import IndexIngestedPassages
from evidence_corpus.domain.events import PassageRevertedFromIndex
from evidence_corpus.domain.published import PassageView

from .contract_helpers import field_names, method_names, parameter_names


class TestIndexWriterPort:
    def test_upserts_passages_and_can_withdraw_them(self) -> None:
        assert method_names(IndexWriterPort) == {"upsert_passages", "revert_passage"}

    def test_upsert_is_keyed_by_document_so_reindexing_is_idempotent(self) -> None:
        assert parameter_names(IndexWriterPort.upsert_passages) == [
            "self",
            "document_id",
            "passages",
        ]

    def test_upsert_returns_the_published_index_manifest(self) -> None:
        annotation = inspect.signature(IndexWriterPort.upsert_passages).return_annotation

        assert annotation == "IndexManifestView"

    def test_withdrawal_requires_a_reason(self) -> None:
        assert parameter_names(IndexWriterPort.revert_passage) == [
            "self",
            "passage_id",
            "reason",
        ]

    def test_writer_consumes_published_views_not_orm_rows(self) -> None:
        annotation = (
            inspect.signature(IndexWriterPort.upsert_passages).parameters["passages"].annotation
        )

        assert annotation == "Sequence[PassageView]"


class TestIndexUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(IndexIngestedPassages.execute) == ["self", "request"]
        assert field_names(IndexIngestedPassagesRequest) == ["document_id"]

    def test_returns_the_index_manifest_view(self) -> None:
        assert (
            inspect.signature(IndexIngestedPassages.execute).return_annotation
            == "IndexManifestView"
        )

    def test_manifest_view_is_immutable(self) -> None:
        view = IndexManifestView(
            index_version="idx-1",
            embedding_model="text-embedding-3-small",
            searchable_since=datetime(2026, 11, 5, tzinfo=UTC),
            passage_count=1,
        )

        with pytest.raises(AttributeError):
            view.passage_count = 2  # type: ignore[misc]


class TestRetraction:
    def test_reverted_passage_event_is_named_and_auditable(self) -> None:
        assert field_names(PassageRevertedFromIndex) == ["passage_id", "reason"]
        assert PassageRevertedFromIndex.name == "PassageRevertedFromIndex"

    def test_reverted_passage_is_not_deleted_from_the_contract(self) -> None:
        """Withdrawal is a state, not a disappearance: the passage id stays queryable."""
        event = PassageRevertedFromIndex(passage_id="psg_1", reason="retraction")

        assert event.passage_id == "psg_1"


class TestSearchableContract:
    def test_tsvector_and_embedding_are_index_side_concerns(self) -> None:
        assert "tsvector" not in inspect.getsource(IndexWriterPort).lower()
        assert "embedding" not in inspect.getsource(IndexWriterPort).lower()

    def test_published_view_is_the_index_input(self) -> None:
        assert "text" in field_names(PassageView)
