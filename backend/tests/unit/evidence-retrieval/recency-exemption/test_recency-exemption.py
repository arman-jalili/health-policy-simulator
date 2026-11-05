"""Contract freeze: non-perishable sources keep full recency weight."""

from __future__ import annotations

from datetime import date

from tests.unit.evidence_retrieval_contract_helpers import parameter_names

from evidence_corpus.domain.values import SourceType
from evidence_retrieval.domain.services import ApplyRecencyPolicy
from evidence_retrieval.domain.values import RecencyPolicy


def test_default_policy_exempts_legislation() -> None:
    policy = RecencyPolicy()

    assert policy.is_exempt(SourceType.LEGISLATION) is True
    assert policy.is_exempt(SourceType.PRESS_REPORT) is False
    assert policy.half_life_days > 0


def test_policy_is_configurable_and_not_a_global_constant() -> None:
    policy = RecencyPolicy(
        half_life_days=30,
        exempt_source_types=frozenset({SourceType.SCIENTIFIC_STUDY}),
    )

    assert policy.is_exempt(SourceType.SCIENTIFIC_STUDY) is True
    assert policy.is_exempt(SourceType.LEGISLATION) is False


def test_apply_service_takes_an_explicit_as_of_date() -> None:
    parameters = parameter_names(ApplyRecencyPolicy.apply)

    assert parameters == ["self", "policy", "published_on", "source_type", "as_of"]
    assert ApplyRecencyPolicy.apply.__annotations__["as_of"] is not None


def test_a_1995_statute_and_a_1995_press_report_are_distinguishable() -> None:
    policy = RecencyPolicy()

    assert policy.is_exempt(SourceType.LEGISLATION) is True
    assert policy.is_exempt(SourceType.PRESS_REPORT) is False
    assert date(1995, 1, 1) < date(2026, 1, 1)
