"""GC-002: a personal quotation is rejected."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from governance_compliance.application.rules import (
    GuardRuleChain,
    PersonalQuotationRule,
    RuleResult,
    context_for,
)
from governance_compliance.application.values import (
    GuardDecision,
    InstitutionalAllowlist,
    SpeakerKind,
)

ALLOWLIST = InstitutionalAllowlist()


def _run(text: str, speaker_kind: SpeakerKind) -> Sequence[RuleResult]:
    return asyncio.run(
        GuardRuleChain([PersonalQuotationRule()]).evaluate(
            context_for(
                text=text,
                speaker_kind=speaker_kind,
                allowlist=ALLOWLIST,
                cited_passage_ids=(),
                reference_figure_ids=(),
            )
        )
    )


def test_person_quotation_is_rejected() -> None:
    results = _run('Der Minister sagte: "Die Reform ist beschlossen."', SpeakerKind.PERSON)

    assert results[-1].decision is GuardDecision.REJECT
    assert results[-1].violation_class is not None
    assert results[-1].violation_class.value == "personal_quotation"


def test_institution_quotation_is_not_rejected_by_gc_002() -> None:
    results = _run('Das BMSGPK sagte: "Die Reform ist beschlossen."', SpeakerKind.INSTITUTION)

    assert results[-1].decision is GuardDecision.ACCEPT
