"""Contract freeze: `SpeakerKind` classification.

Invariant 5 is a governance requirement, not a formatting preference: a quotation attributed to a
natural person may never become citable evidence, while an institutional statement stays citable
with its attribution. The contract fixes the vocabulary, the citability policy and the events.
"""

from __future__ import annotations

import pytest

from evidence_corpus.domain.entities import Article, Document
from evidence_corpus.domain.events import (
    InstitutionalStatementAttributed,
    PersonalQuotationExcluded,
    QuotationBlockDetected,
)
from evidence_corpus.domain.values import (
    CITABLE_SPEAKER_KINDS,
    Offsets,
    QuotationBlock,
    SpeakerKind,
)

from .contract_helpers import enum_values, field_names


class TestSpeakerVocabulary:
    def test_has_exactly_three_attribution_classes(self) -> None:
        assert enum_values(SpeakerKind) == {"institution", "person", "anonymous"}

    def test_citability_policy_is_frozen_as_data(self) -> None:
        assert frozenset({SpeakerKind.INSTITUTION}) == CITABLE_SPEAKER_KINDS

    @pytest.mark.parametrize("kind", [SpeakerKind.PERSON, SpeakerKind.ANONYMOUS])
    def test_non_institutional_attribution_is_never_citable(self, kind: SpeakerKind) -> None:
        assert kind not in CITABLE_SPEAKER_KINDS


class TestQuotationBlock:
    def test_retains_span_and_attribution_together(self) -> None:
        block = QuotationBlock(
            text="„Das ist ein Skandal“, sagte Müller.",
            speaker_kind=SpeakerKind.PERSON,
            offsets=Offsets(0, 38),
        )

        assert block.speaker_kind is SpeakerKind.PERSON
        assert field_names(QuotationBlock) == ["text", "speaker_kind", "offsets"]


class TestClassificationEvents:
    def test_person_quotation_exclusion_is_recorded_with_its_span(self) -> None:
        assert field_names(PersonalQuotationExcluded) == ["passage_id", "span"]
        assert PersonalQuotationExcluded.name == "PersonalQuotationExcluded"

    def test_institutional_statement_keeps_the_institution_identity(self) -> None:
        assert field_names(InstitutionalStatementAttributed) == [
            "passage_id",
            "institution_identity",
        ]

    def test_detection_event_precedes_the_citability_decision(self) -> None:
        assert field_names(QuotationBlockDetected) == ["passage_id", "speaker_kind"]
        assert QuotationBlockDetected.name == "QuotationBlockDetected"

    def test_events_are_immutable_facts(self) -> None:
        event = InstitutionalStatementAttributed(
            passage_id="psg_01J0000000000000000000000C",
            institution_identity="Hauptverband der Sozialversicherungsträger",
        )

        with pytest.raises(AttributeError):
            event.institution_identity = "other"  # type: ignore[misc]


class TestAggregateGate:
    def test_only_the_aggregate_decides_what_leaves_it(self) -> None:
        assert "publishable_passages" in dir(Document)
        assert "publishable_passages" in dir(Article)

    def test_article_retains_quotation_blocks_for_audit(self) -> None:
        assert "quotation_blocks" in field_names(Article)
