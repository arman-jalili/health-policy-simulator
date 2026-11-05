"""GC-004: an uncited factual claim becomes unsupported, never accept."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from governance_compliance.application.rules import (
    GuardRuleChain,
    RuleResult,
    UnsupportedFactRule,
    context_for,
)
from governance_compliance.application.values import (
    GuardDecision,
    InstitutionalAllowlist,
    SpeakerKind,
)


def _run(text: str, cited: tuple[str, ...] = ()) -> Sequence[RuleResult]:
    return asyncio.run(
        GuardRuleChain([UnsupportedFactRule()]).evaluate(
            context_for(
                text=text,
                speaker_kind=SpeakerKind.INSTITUTION,
                allowlist=InstitutionalAllowlist(),
                cited_passage_ids=cited,
                reference_figure_ids=(),
            )
        )
    )


def test_uncited_fact_is_rewritten_to_unsupported() -> None:
    result = _run("Die Ausgaben steigen 2026 um 4,2 Prozent.")[-1]

    assert result.decision is GuardDecision.REWRITE
    assert result.violation_class is not None
    assert result.violation_class.value == "unsupported_fact"
    assert (result.rewritten_text or "").startswith("unsupported:")


def test_cited_fact_is_accepted() -> None:
    result = _run("Die Ausgaben steigen 2026 um 4,2 Prozent.", ("psg_1",))[-1]

    assert result.decision is GuardDecision.ACCEPT
