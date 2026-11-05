"""Contract freeze: value objects and frozen enums of EvidenceCorpus.

Every assertion here is part of the frozen contract. Changing a field name, an enum member or a
rubric constant requires re-opening the contract issue, not a drive-by edit in an implementation PR.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from enum import StrEnum

import pytest

from evidence_corpus.domain.values import (
    AUTHORITY_RULES,
    CITABLE_SPEAKER_KINDS,
    DEFAULT_MINIMUM_CONFIDENCE,
    LANGUAGE_DE_AT,
    ArticleDraft,
    ArticleSection,
    AuthorityRule,
    AuthorityTier,
    CanonicalArticleRef,
    ClaimType,
    ExtractionMethod,
    ExtractionQuality,
    LanguageTag,
    Offsets,
    PageTextFacts,
    Provenance,
    QuotationBlock,
    SourceType,
    SpeakerKind,
    authority_rule,
)

from .contract_helpers import enum_values, field_names


class TestOffsets:
    def test_holds_start_and_end(self) -> None:
        offsets = Offsets(start=10, end=42)

        assert (offsets.start, offsets.end) == (10, 42)

    def test_is_immutable_and_equal_by_state(self) -> None:
        assert Offsets(0, 5) == Offsets(0, 5)
        with pytest.raises(dataclasses.FrozenInstanceError):
            Offsets(0, 5).start = 1  # type: ignore[misc]


class TestLanguageTag:
    def test_holds_a_bcp47_tag(self) -> None:
        assert LanguageTag("de-AT").tag == "de-AT"

    def test_has_a_frozen_german_austrian_constant(self) -> None:
        assert LanguageTag("de-AT") == LANGUAGE_DE_AT


class TestProvenance:
    def test_is_a_complete_locator_bundle(self) -> None:
        assert field_names(Provenance) == [
            "outlet",
            "published_on",
            "medium",
            "page_from",
            "page_to",
            "offsets",
            "source_uri",
        ]

    def test_is_frozen(self) -> None:
        provenance = Provenance(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=3,
            page_to=3,
            offsets=Offsets(120, 240),
            source_uri="s3://corpus/std-2026-10-01.pdf",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            provenance.outlet = "Kurier"  # type: ignore[misc]


class TestExtractionQuality:
    def test_declares_method_confidence_and_glyph_rate(self) -> None:
        assert field_names(ExtractionQuality)[:3] == [
            "method",
            "confidence",
            "missing_glyph_rate",
        ]

    def test_acceptance_threshold_is_frozen_at_contract_level(self) -> None:
        assert pytest.approx(0.85) == DEFAULT_MINIMUM_CONFIDENCE

    def test_quality_gate_accepts_good_extraction(self) -> None:
        quality = ExtractionQuality(
            method=ExtractionMethod.NATIVE,
            confidence=0.95,
            missing_glyph_rate=0.0,
        )

        assert quality.is_acceptable() is True

    def test_quality_gate_requires_both_confidence_and_low_glyph_damage(self) -> None:
        low_confidence = ExtractionQuality(ExtractionMethod.OCR, 0.6, 0.0)
        glyph_damage = ExtractionQuality(ExtractionMethod.OCR, 0.95, 0.4)

        assert low_confidence.is_acceptable() is False
        assert glyph_damage.is_acceptable() is False

    def test_gate_signature_accepts_an_override_threshold(self) -> None:
        parameters = field_names(ExtractionQuality)
        assert "confidence" in parameters
        assert ExtractionQuality.is_acceptable.__defaults__ == (DEFAULT_MINIMUM_CONFIDENCE,)


class TestEnums:
    def test_extraction_methods_are_native_and_ocr(self) -> None:
        assert enum_values(ExtractionMethod) == {"native", "ocr"}

    def test_authority_tiers_are_the_exploration_rubric(self) -> None:
        assert enum_values(AuthorityTier) == {
            "official_statistics",
            "legislation",
            "scientific_study",
            "institutional_statement",
            "press_report",
            "other",
        }

    def test_source_types_add_an_explicit_unknown(self) -> None:
        assert enum_values(SourceType) == {
            "official_statistics",
            "legislation",
            "scientific_study",
            "institutional_statement",
            "press_report",
            "other",
            "unknown",
        }

    def test_speaker_kinds_are_institution_person_anonymous(self) -> None:
        assert enum_values(SpeakerKind) == {"institution", "person", "anonymous"}

    def test_claim_types_are_the_published_vocabulary(self) -> None:
        assert enum_values(ClaimType) == {"quantitative", "legal", "causal", "qualitative"}

    def test_article_sections_are_typed_regions(self) -> None:
        assert enum_values(ArticleSection) == {
            "headline",
            "standfirst",
            "body",
            "caption",
            "quotation",
        }

    def test_enums_serialise_as_plain_strings(self) -> None:
        assert issubclass(AuthorityTier, StrEnum)
        assert str(AuthorityTier.LEGISLATION) == "legislation"


class TestAuthorityRules:
    def test_every_claim_type_has_a_rule(self) -> None:
        assert set(AUTHORITY_RULES) == set(ClaimType)

    def test_legal_rules_rank_legislation_above_press(self) -> None:
        order = AUTHORITY_RULES[ClaimType.LEGAL]

        assert order.index(SourceType.LEGISLATION) < order.index(SourceType.PRESS_REPORT)

    def test_quantitative_rules_rank_official_statistics_first(self) -> None:
        assert AUTHORITY_RULES[ClaimType.QUANTITATIVE][0] is SourceType.OFFICIAL_STATISTICS

    def test_causal_rules_rank_studies_first(self) -> None:
        assert AUTHORITY_RULES[ClaimType.CAUSAL][0] is SourceType.SCIENTIFIC_STUDY

    def test_press_ranks_below_the_authoritative_source_types(self) -> None:
        for claim_type, order in AUTHORITY_RULES.items():
            press = order.index(SourceType.PRESS_REPORT)
            assert press > 0, claim_type
            assert press == len(order) - 2, claim_type
            assert order[-1] is SourceType.OTHER, claim_type

    def test_rules_are_immutable(self) -> None:
        with pytest.raises(TypeError):
            AUTHORITY_RULES[ClaimType.LEGAL] = ()  # type: ignore[index]

    def test_authority_rule_bundles_claim_type_and_ordering(self) -> None:
        rule = authority_rule(ClaimType.LEGAL)

        assert isinstance(rule, AuthorityRule)
        assert rule.claim_type is ClaimType.LEGAL
        assert rule.ordered_source_types == AUTHORITY_RULES[ClaimType.LEGAL]


class TestSpeakerCitability:
    def test_only_institutional_statements_are_citable(self) -> None:
        assert frozenset({SpeakerKind.INSTITUTION}) == CITABLE_SPEAKER_KINDS

    def test_person_attributed_quotations_are_never_citable(self) -> None:
        assert SpeakerKind.PERSON not in CITABLE_SPEAKER_KINDS
        assert SpeakerKind.ANONYMOUS not in CITABLE_SPEAKER_KINDS


class TestStructuralValueObjects:
    def test_quotation_block_carries_span_and_attribution(self) -> None:
        assert field_names(QuotationBlock) == ["text", "speaker_kind", "offsets"]

    def test_canonical_article_ref_points_at_the_owner_of_citations(self) -> None:
        assert field_names(CanonicalArticleRef) == ["canonical_article_id", "similarity"]

    def test_page_text_facts_drive_the_native_vs_ocr_decision(self) -> None:
        assert field_names(PageTextFacts) == [
            "has_text_layer",
            "average_chars_per_page",
            "missing_glyph_rate",
        ]

    def test_article_draft_is_what_a_boundary_strategy_emits(self) -> None:
        assert field_names(ArticleDraft) == ["headline", "body", "page_from", "page_to"]


class TestValueObjectValidation:
    """A value object that exists is a value object that is valid."""

    @pytest.mark.parametrize(
        "quality",
        [
            {"confidence": 1.4, "missing_glyph_rate": 0.0},
            {"confidence": -0.1, "missing_glyph_rate": 0.0},
            {"confidence": 0.9, "missing_glyph_rate": 1.5},
            {"confidence": 0.9, "missing_glyph_rate": 0.0, "page_count": 0},
        ],
    )
    def test_extraction_quality_rejects_impossible_measurements(
        self, quality: dict[str, float]
    ) -> None:
        with pytest.raises(ValueError, match=r"confidence|glyph|page_count"):
            ExtractionQuality(method=ExtractionMethod.NATIVE, **quality)  # type: ignore[arg-type]

    @pytest.mark.parametrize("tag", ["", "de_AT", "DE", "d", "de-AT-"])
    def test_language_tag_rejects_malformed_bcp47(self, tag: str) -> None:
        with pytest.raises(ValueError, match="BCP-47"):
            LanguageTag(tag)

    def test_language_tag_renders_as_its_tag(self) -> None:
        assert str(LanguageTag("de-AT")) == "de-AT"

    @pytest.mark.parametrize("value", [-1, 0, 5])
    def test_offsets_reject_degenerate_spans(self, value: int) -> None:
        with pytest.raises(ValueError, match="offset"):
            Offsets(start=value, end=value)

    def test_offsets_report_length_overlap_and_containment(self) -> None:
        span = Offsets(10, 20)

        assert span.length == 10
        assert span.overlaps(Offsets(15, 25)) is True
        assert span.overlaps(Offsets(20, 30)) is False
        assert span.within(20) is True
        assert span.within(15) is False

    @pytest.mark.parametrize(
        "provenance",
        [
            {"outlet": "", "medium": "print", "page_from": 1, "page_to": 1},
            {"outlet": "Der Standard", "medium": "pigeon", "page_from": 1, "page_to": 1},
            {"outlet": "Der Standard", "medium": "print", "page_from": 0, "page_to": 1},
            {"outlet": "Der Standard", "medium": "print", "page_from": 3, "page_to": 2},
        ],
    )
    def test_provenance_rejects_unresolvable_locators(self, provenance: dict[str, object]) -> None:
        with pytest.raises(ValueError, match=r"outlet|medium|page|source URI"):
            Provenance(
                published_on=date(2026, 10, 1),
                offsets=Offsets(0, 10),
                source_uri="s3://corpus/std.pdf",
                **provenance,  # type: ignore[arg-type]
            )

    def test_provenance_accepts_a_complete_locator(self) -> None:
        provenance = Provenance(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=3,
            page_to=3,
            offsets=Offsets(120, 240),
            source_uri="s3://corpus/std.pdf",
        )

        assert provenance.page_from == 3

    def test_authority_rule_rejects_unknown_duplicates_and_empty_rules(self) -> None:
        with pytest.raises(ValueError, match="unknown"):
            AuthorityRule(ClaimType.LEGAL, (SourceType.UNKNOWN,))
        with pytest.raises(ValueError, match="repeat"):
            AuthorityRule(ClaimType.LEGAL, (SourceType.LEGISLATION, SourceType.LEGISLATION))
        with pytest.raises(ValueError, match="at least one"):
            AuthorityRule(ClaimType.LEGAL, ())

    def test_canonical_reference_similarity_is_bounded(self) -> None:
        with pytest.raises(ValueError, match="similarity"):
            CanonicalArticleRef("art_1", 1.5)
        with pytest.raises(ValueError, match="canonical"):
            CanonicalArticleRef("", 0.9)

    def test_article_draft_requires_headline_body_and_ordered_pages(self) -> None:
        with pytest.raises(ValueError, match="headline"):
            ArticleDraft("", "body", 1, 1)
        with pytest.raises(ValueError, match="body"):
            ArticleDraft("headline", " ", 1, 1)
        with pytest.raises(ValueError, match="page range"):
            ArticleDraft("headline", "body", 3, 2)

    def test_quotation_block_requires_text(self) -> None:
        with pytest.raises(ValueError, match="text"):
            QuotationBlock("   ", SpeakerKind.PERSON, Offsets(0, 1))
