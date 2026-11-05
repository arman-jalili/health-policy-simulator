"""Contract freeze: `ClassifySourceAuthority`.

Invariant 6/7 and AC 8: authority is claim-type relative, and an unknown source type can never be
promoted. The rubric is frozen as data so an implementation cannot quietly re-rank press above
statute for legal claims.
"""

from __future__ import annotations

import inspect

import pytest

from evidence_corpus.application.commands import ClassifySourceAuthorityRequest
from evidence_corpus.application.dto import ClassifyAuthorityResult
from evidence_corpus.application.services import ClassifySourceAuthority
from evidence_corpus.domain.events import AuthorityTierAssigned, DuplicateArticleLinked
from evidence_corpus.domain.repositories import AuthorityRuleRepository
from evidence_corpus.domain.values import (
    AUTHORITY_RULES,
    AuthorityRule,
    AuthorityTier,
    ClaimType,
    SourceType,
    authority_rule,
)

from .contract_helpers import field_names, parameter_names


class TestUnknownSourceType:
    def test_unknown_source_type_is_refused(self) -> None:
        from evidence_corpus.domain.errors import SourceTypeUnknown

        error = SourceTypeUnknown("doc_01J0000000000000000000000A")

        assert error.code == "SOURCE_TYPE_UNKNOWN"
        assert error.status_code == 422

    def test_unknown_is_a_declared_but_unusable_source_type(self) -> None:
        assert SourceType.UNKNOWN.value == "unknown"
        assert SourceType.UNKNOWN not in AUTHORITY_RULES[ClaimType.LEGAL]

    def test_authority_tier_assignment_cannot_be_repeated(self) -> None:
        from evidence_corpus.domain.errors import AuthorityAlreadyAssigned

        assert AuthorityAlreadyAssigned.code == "AUTHORITY_ALREADY_ASSIGNED"


class TestClaimTypeRelativeRubric:
    @pytest.mark.parametrize("claim_type", list(ClaimType))
    def test_every_claim_type_has_a_complete_rule(self, claim_type: ClaimType) -> None:
        rule = authority_rule(claim_type)

        assert isinstance(rule, AuthorityRule)
        assert set(rule.ordered_source_types) >= {
            SourceType.LEGISLATION,
            SourceType.OFFICIAL_STATISTICS,
            SourceType.SCIENTIFIC_STUDY,
            SourceType.INSTITUTIONAL_STATEMENT,
            SourceType.PRESS_REPORT,
        }

    def test_legal_claims_rank_legislation_above_press(self) -> None:
        order = authority_rule(ClaimType.LEGAL).ordered_source_types

        assert order.index(SourceType.LEGISLATION) < order.index(SourceType.PRESS_REPORT)

    def test_quantitative_claims_rank_statistics_above_press(self) -> None:
        order = authority_rule(ClaimType.QUANTITATIVE).ordered_source_types

        assert order.index(SourceType.OFFICIAL_STATISTICS) < order.index(SourceType.PRESS_REPORT)

    def test_causal_claims_rank_studies_above_press(self) -> None:
        order = authority_rule(ClaimType.CAUSAL).ordered_source_types

        assert order.index(SourceType.SCIENTIFIC_STUDY) < order.index(SourceType.PRESS_REPORT)

    def test_rubric_tiers_are_the_assignable_vocabulary(self) -> None:
        from evidence_corpus.domain.values import AuthorityTier

        assignable = {tier.value for tier in AuthorityTier}
        rule_values = {
            source.value for source in authority_rule(ClaimType.LEGAL).ordered_source_types
        }

        assert rule_values <= assignable | {"other"}


class TestClassifyUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(ClassifySourceAuthority.execute) == ["self", "request"]
        assert field_names(ClassifySourceAuthorityRequest) == ["document_id"]

    def test_result_reports_tier_and_duplicates(self) -> None:
        assert field_names(ClassifyAuthorityResult) == [
            "document_id",
            "tier",
            "duplicate_article_ids",
        ]

    def test_returns_the_assigned_tier_type(self) -> None:
        annotation = inspect.signature(ClassifySourceAuthority.execute).return_annotation

        assert annotation == "ClassifyAuthorityResult"


class TestAuthorityEvents:
    def test_tier_assignment_payload_is_minimal(self) -> None:
        assert field_names(AuthorityTierAssigned) == ["document_id", "tier"]

    def test_duplicate_linking_records_similarity(self) -> None:
        assert field_names(DuplicateArticleLinked) == [
            "article_id",
            "canonical_article_id",
            "similarity",
        ]


class TestAuthorityRuleRepository:
    def test_repository_is_owned_by_the_domain(self) -> None:
        assert getattr(AuthorityRuleRepository, "_is_protocol", False) is True

    def test_lookup_is_by_claim_type_and_supports_listing(self) -> None:
        assert {"for_claim_type", "list_all"} <= {
            name for name in dir(AuthorityRuleRepository) if not name.startswith("_")
        }

    def test_authority_tier_is_a_value_not_an_entity(self) -> None:
        assert AuthorityTier.LEGISLATION.value == "legislation"
