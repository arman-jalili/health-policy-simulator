"""GC-003: a person-owned ministry reference resolves canonically or rejects."""

from __future__ import annotations

import asyncio

from governance_compliance.application.rules import (
    GuardRuleChain,
    InstitutionAliasRule,
    context_for,
)
from governance_compliance.application.values import (
    AllowlistEntry,
    GuardDecision,
    InstitutionalAllowlist,
    SpeakerKind,
)
from governance_compliance.infrastructure.resolver import AllowlistInstitutionResolver

CANONICAL = "Bundesministerium für Soziales, Gesundheit, Pflege und Konsumentenschutz"
ALLOWLIST = InstitutionalAllowlist(
    institutions=(
        AllowlistEntry(
            code="bmsgpk",
            canonical_name=CANONICAL,
            short_name="BMSGPK",
            category="ministry",
            aliases=("the minister's ministry",),
        ),
    )
)


def _run(text: str, allowlist: InstitutionalAllowlist):
    return asyncio.run(
        GuardRuleChain([InstitutionAliasRule(AllowlistInstitutionResolver())]).evaluate(
            context_for(
                text=text,
                speaker_kind=SpeakerKind.INSTITUTION,
                allowlist=allowlist,
                cited_passage_ids=(),
                reference_figure_ids=(),
            )
        )
    )


def test_person_owned_ministry_resolves_to_the_canonical_name() -> None:
    result = _run("The minister's ministry confirmed the plan.", ALLOWLIST)[-1]

    assert result.decision is GuardDecision.REWRITE
    assert CANONICAL in (result.rewritten_text or "")


def test_unresolved_person_owned_ministry_is_rejected() -> None:
    result = _run("The minister's ministry confirmed the plan.", InstitutionalAllowlist())[-1]

    assert result.decision is GuardDecision.REJECT
    assert result.violation_class.value == "institution_ambiguous"
