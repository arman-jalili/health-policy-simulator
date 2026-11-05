"""Contract freeze: provenance resolution.

`GET /api/v1/passages/{id}` must reproduce the exact slice from the source file. That makes the
published `PassageView`/`ProvenanceView` contract load-bearing for EvidenceRetrieval and
DecisionBrief, so it is frozen here with explicit field names.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date

import pytest

import evidence_corpus.domain.published as published_module
from evidence_corpus.application.commands import ResolvePassageRequest
from evidence_corpus.application.services import ResolvePassage
from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Offsets, SpeakerKind

from .contract_helpers import field_names, parameter_names


class TestProvenanceView:
    def test_resolves_outlet_date_page_and_offsets(self) -> None:
        assert field_names(ProvenanceView) == [
            "outlet",
            "published_on",
            "medium",
            "page_from",
            "page_to",
            "offsets",
            "source_uri",
        ]

    def test_is_immutable_so_a_citation_cannot_be_rewritten(self) -> None:
        view = ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=3,
            page_to=3,
            offsets=Offsets(120, 240),
            source_uri="s3://corpus/std-2026-10-01.pdf",
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            view.page_from = 4  # type: ignore[misc]


class TestPassageView:
    def test_matches_the_documented_api_payload(self) -> None:
        names = field_names(PassageView)

        assert {"passage_id", "text", "provenance", "speaker_kind", "citable"} <= set(names)

    def test_carries_its_article_and_document_for_traceability(self) -> None:
        assert {"article_id", "document_id"} <= set(field_names(PassageView))

    def test_speaker_kind_is_exposed_so_consumers_never_re_derive_it(self) -> None:
        assert "speaker_kind" in field_names(PassageView)
        assert SpeakerKind.INSTITUTION.value == "institution"

    def test_view_is_framework_free(self) -> None:
        source = inspect.getsource(published_module)

        assert "import sqlalchemy" not in source
        assert "import pydantic" not in source
        assert "import fastapi" not in source


class TestResolvePassageUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(ResolvePassage.execute) == ["self", "request"]
        assert field_names(ResolvePassageRequest) == ["passage_id"]

    def test_returns_the_published_view(self) -> None:
        assert inspect.signature(ResolvePassage.execute).return_annotation == "PassageView"

    def test_repository_exposes_passage_lookup(self) -> None:
        from evidence_corpus.domain.repositories import PassageRepository

        assert "get" in dir(PassageRepository)
        assert "list_by_document" in dir(PassageRepository)
