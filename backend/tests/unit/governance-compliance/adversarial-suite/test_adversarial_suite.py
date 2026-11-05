"""Adversarial regression suite: 30 strings are never accepted by the guard."""

from __future__ import annotations

import asyncio

import pytest

from governance_compliance.application.rules import (
    ContradictedFigureRule,
    GuardRuleChain,
    InstitutionAliasRule,
    PersonalQuotationRule,
    PersonReferenceRule,
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

PERSON_STRINGS = [
    "Dr. Müller sagte, die Reform sei notwendig.",
    "Mag. Berger fordert mehr Geld.",
    "Prof. Huber kritisiert den Plan.",
    "Obmann Weber stimmte zu.",
    "Präsidentin Mayr lehnt ab.",
    "Dipl.-Ing. Gruber warnt.",
    "Dr. Müller und Mag. Berger trafen sich.",
    "Prof. Huber sagte: Die Lage ist ernst.",
    "Obmann Weber: Wir brauchen Zeit.",
    "Präsident Maier sprach.",
]

QUOTE_STRINGS = [
    'Der Minister sagte: "Die Reform ist gut."',
    '"Wir werden zustimmen", sagte der Präsident.',
    'Die Ministerin erklärte: "Das ist beschlossen."',
    'Der Obmann betonte: "Wir bleiben hart."',
    '"Das ist falsch", sagte Dr. Müller.',
    'Der Präsident sagte: "Wir prüfen das."',
    'Die Ministerin sagte: "Mehr Geld ist nötig."',
    '"Wir lehnen ab", so der Obmann.',
    'Der Minister: "Der Plan steht."',
    'Die Präsidentin sagte: "Wir sind bereit."',
]

FACT_STRINGS = [
    "Die Ausgaben steigen 2026 um 4,2 Prozent.",
    "Die Kosten betragen 12 Milliarden Euro.",
    "Die Zahl der Ärzte sinkt auf 8.000.",
    "Das Budget steigt um 3 Prozent.",
    "Die Wartezeit beträgt 42 Tage.",
    "Die Prämien erhöhen sich 2027.",
    "Die Prognose liegt bei 5,1 Prozent.",
    "Die Ausgaben sinken um 2 Milliarden.",
    "Die Kosten steigen auf 9,8 Milliarden.",
    "Die Zahl der Kassenstellen sinkt.",
]


def _verdict(text: str, speaker_kind: SpeakerKind) -> GuardDecision:
    chain = GuardRuleChain(
        [
            PersonReferenceRule(RegexPersonNameDetector()),
            PersonalQuotationRule(RegexPersonNameDetector()),
            InstitutionAliasRule(AllowlistInstitutionResolver()),
            UnsupportedFactRule(),
            ContradictedFigureRule(UnknownFigureVerdicts()),
        ]
    )
    results = asyncio.run(
        chain.evaluate(
            context_for(
                text=text,
                speaker_kind=speaker_kind,
                allowlist=ALLOWLIST,
                cited_passage_ids=(),
                reference_figure_ids=(),
            )
        )
    )
    if any(result.decision is GuardDecision.REJECT for result in results):
        return GuardDecision.REJECT
    if any(result.decision is GuardDecision.REWRITE for result in results):
        return GuardDecision.REWRITE
    return GuardDecision.ACCEPT


@pytest.mark.parametrize("text", PERSON_STRINGS)
def test_person_strings_are_never_accepted(text: str) -> None:
    assert _verdict(text, SpeakerKind.INSTITUTION) is not GuardDecision.ACCEPT


@pytest.mark.parametrize("text", QUOTE_STRINGS)
def test_person_quotes_are_never_accepted(text: str) -> None:
    assert _verdict(text, SpeakerKind.PERSON) is not GuardDecision.ACCEPT


@pytest.mark.parametrize("text", FACT_STRINGS)
def test_uncited_facts_are_never_accepted(text: str) -> None:
    assert _verdict(text, SpeakerKind.INSTITUTION) is not GuardDecision.ACCEPT
