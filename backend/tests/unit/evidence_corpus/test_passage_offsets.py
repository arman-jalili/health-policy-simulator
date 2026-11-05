"""Contract freeze: `Passage.offsets` and the boundaries that keep citations honest.

Invariant 3: offsets must lie inside the parent article text and must not overlap siblings.
The contract fixes the value object, the two failure modes and where validation happens.
"""

from __future__ import annotations

import pytest

from evidence_corpus.domain.entities import Article, Document, Passage
from evidence_corpus.domain.errors import OffsetsOutOfBounds, OverlappingPassages
from evidence_corpus.domain.values import ArticleSection, Offsets, SpeakerKind

from .contract_helpers import field_names, parameter_names


class TestOffsetsValue:
    def test_is_a_half_open_interval(self) -> None:
        offsets = Offsets(start=5, end=6)

        assert (offsets.start, offsets.end) == (5, 6)

    def test_equality_is_by_state_not_identity(self) -> None:
        assert Offsets(3, 9) == Offsets(3, 9)
        assert Offsets(3, 9) != Offsets(3, 10)
        assert hash(Offsets(3, 9)) == hash(Offsets(3, 9))

    @pytest.mark.parametrize(("start", "end"), [(0, 1), (4, 9), (100, 101)])
    def test_construction_is_unvalidated_at_contract_stage(self, start: int, end: int) -> None:
        """Bounds validation belongs to the passage-offsets issue, not to the freeze."""
        assert (Offsets(start, end).start, Offsets(start, end).end) == (start, end)


class TestBoundaryFailures:
    def test_out_of_bounds_offsets_are_a_client_error(self) -> None:
        error = OffsetsOutOfBounds(article_id="art_1", start=900, end=950, article_length=100)

        assert error.code == "OFFSETS_OUT_OF_BOUNDS"
        assert error.status_code == 422
        assert "art_1" in str(error)

    def test_overlapping_siblings_are_a_conflict(self) -> None:
        error = OverlappingPassages(article_id="art_1", first="psg_1", second="psg_2")

        assert error.code == "PASSAGE_OVERLAP"
        assert error.status_code == 409

    def test_codes_are_distinct(self) -> None:
        assert OffsetsOutOfBounds.code != OverlappingPassages.code


class TestPassageOffsets:
    def test_passage_carries_offsets_instead_of_free_text(self) -> None:
        names = field_names(Passage)

        assert "offsets" in names
        assert "text" in names

    def test_passage_declares_its_section_and_attribution(self) -> None:
        passage = Passage(
            id="psg_01J0000000000000000000000C",
            article_id="art_01J0000000000000000000000B",
            document_id="doc_01J0000000000000000000000A",
            ord=0,
            text="Text",
            offsets=Offsets(0, 4),
            speaker_kind=SpeakerKind.INSTITUTION,
            citable=True,
        )

        assert passage.section is ArticleSection.BODY
        assert isinstance(passage.offsets, Offsets)


class TestArticleBounds:
    def test_article_exposes_the_bounds_used_for_validation(self) -> None:
        assert {"page_from", "page_to", "language", "body"} <= set(field_names(Article))

    def test_document_add_article_takes_bounds_from_the_strategy(self) -> None:
        assert parameter_names(Document.add_article) == [
            "self",
            "headline",
            "body",
            "page_from",
            "page_to",
        ]

    def test_overlap_guard_is_declared_on_the_article_interface(self) -> None:
        assert "publishable_passages" in dir(Article)


class TestPassageSpanDiscipline:
    """A citation is reproducible only if its span is exactly inside the article and unique."""

    def test_ordinals_follow_insertion_order(self) -> None:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.values import (
            ExtractionMethod,
            ExtractionQuality,
            LanguageTag,
            SourceType,
        )

        document = Document.register(
            source_uri="s3://corpus/std.pdf",
            content_hash="sha256:abc",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction("Text", ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0))
        article = document.add_article("h", "Erster Satz. Zweiter Satz.", 1, 1)

        first = article.add_passage(
            text="Erster Satz.", offsets=Offsets(0, 12), speaker_kind=SpeakerKind.INSTITUTION
        )
        second = article.add_passage(
            text="Zweiter Satz.", offsets=Offsets(13, 25), speaker_kind=SpeakerKind.INSTITUTION
        )

        assert (first.ord, second.ord) == (0, 1)
        assert article.passage_count() == 2

    def test_adjacent_spans_do_not_overlap(self) -> None:
        assert Offsets(0, 10).overlaps(Offsets(10, 20)) is False
        assert Offsets(0, 11).overlaps(Offsets(10, 20)) is True
        assert Offsets(10, 20).overlaps(Offsets(0, 11)) is True

    def test_zero_length_spans_are_impossible(self) -> None:
        with pytest.raises(ValueError, match="end must be greater"):
            Offsets(5, 5)

    def test_negative_offsets_are_impossible(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            Offsets(-1, 5)
