"""Determinism: the same input and rule version yields the same verdict, with no LLM call."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from governance_compliance.application.rules import (
    ContradictedFigureRule,
    GuardRuleChain,
    InstitutionAliasRule,
    PersonalQuotationRule,
    PersonReferenceRule,
    RuleResult,
    UnsupportedFactRule,
    context_for,
)
from governance_compliance.application.values import (
    AllowlistEntry,
    GuardDecision,
    InstitutionalAllowlist,
    SpeakerKind,
)
from governance_compliance.infrastructure.figures import UnknownFigureVerdicts
from governance_compliance.infrastructure.ner import RegexPersonNameDetector
from governance_compliance.infrastructure.resolver import AllowlistInstitutionResolver

ALLOWLIST = InstitutionalAllowlist(
    institutions=(
        AllowlistEntry(
            code="bmsgpk",
            canonical_name="BMSGPK",
            short_name="BMSGPK",
            category="ministry",
        ),
    )
)


def _chain() -> GuardRuleChain:
    return GuardRuleChain(
        [
            PersonReferenceRule(RegexPersonNameDetector()),
            PersonalQuotationRule(RegexPersonNameDetector()),
            InstitutionAliasRule(AllowlistInstitutionResolver()),
            UnsupportedFactRule(),
            ContradictedFigureRule(UnknownFigureVerdicts()),
        ]
    )


def _evaluate(text: str) -> Sequence[RuleResult]:
    return asyncio.run(
        _chain().evaluate(
            context_for(
                text=text,
                speaker_kind=SpeakerKind.PERSON,
                allowlist=ALLOWLIST,
                cited_passage_ids=(),
                reference_figure_ids=(),
            )
        )
    )


def test_same_input_and_rule_version_yield_identical_verdicts() -> None:
    first = _evaluate('Dr. Müller sagte: "Die Ausgaben steigen um 4,2 Prozent."')
    second = _evaluate('Dr. Müller sagte: "Die Ausgaben steigen um 4,2 Prozent."')

    assert [item.decision for item in first] == [item.decision for item in second]
    first_hits = [item for item in first if item.decision is not GuardDecision.ACCEPT]
    second_hits = [item for item in second if item.decision is not GuardDecision.ACCEPT]
    assert first_hits
    assert [item.decision for item in first_hits] == [item.decision for item in second_hits]
    assert first_hits[0].violation_class == second_hits[0].violation_class
    assert first_hits[0].offending_span == second_hits[0].offending_span


def test_guard_context_carries_no_llm_client() -> None:
    annotations = __import__("typing").get_type_hints(
        type(
            context_for(
                text="x",
                speaker_kind=SpeakerKind.INSTITUTION,
                allowlist=ALLOWLIST,
                cited_passage_ids=(),
                reference_figure_ids=(),
            )
        )
    )
    assert "llm" not in " ".join(str(value).lower() for value in annotations.values())
