"""GC-001: a named person is never accepted."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from governance_compliance.application.commands import EnforceInstitutionOnlyOutputRequest
from governance_compliance.application.rules import GuardRuleChain, PersonReferenceRule
from governance_compliance.application.services import EnforceInstitutionOnlyOutput
from governance_compliance.application.values import (
    AllowlistEntry,
    GuardDecision,
    InstitutionalAllowlist,
    InvocationId,
    SpeakerKind,
)
from governance_compliance.infrastructure.ner import RegexPersonNameDetector
from governance_compliance.infrastructure.repository.memory import InMemoryViolationStore

ALLOWLIST = InstitutionalAllowlist(
    institutions=(
        AllowlistEntry(
            code="bmsgpk",
            canonical_name=(
                "Bundesministerium für Soziales, Gesundheit, Pflege und Konsumentenschutz"
            ),
            short_name="BMSGPK",
            category="ministry",
            aliases=("Gesundheitsministerium",),
        ),
    )
)


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


class _Uow:
    class _Txn:
        async def __aenter__(self) -> object:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    def transaction(self) -> _Txn:
        return self._Txn()


def _guard(store: InMemoryViolationStore) -> EnforceInstitutionOnlyOutput:
    detector = RegexPersonNameDetector()
    return EnforceInstitutionOnlyOutput(
        rules=GuardRuleChain([PersonReferenceRule(detector)]),
        allowlist=ALLOWLIST,
        violations=store,
        clock=_Clock(),
        uow=_Uow(),
    )


def test_person_reference_is_never_accepted() -> None:
    store = InMemoryViolationStore()
    result = asyncio.run(
        _guard(store).execute(
            EnforceInstitutionOnlyOutputRequest(
                text="Dr. Müller sagte, die Reform sei notwendig.",
                speaker_kind=SpeakerKind.INSTITUTION,
                invocation_id=InvocationId("inv_1"),
            )
        )
    )

    assert result.decision is not GuardDecision.ACCEPT
    assert result.decision is GuardDecision.REWRITE
    assert "Dr. Müller" not in (result.rewritten_text or "")
    assert len(result.violations) == 1
    assert result.violations[0].violation_class.value == "person_named"
    assert result.violations[0].rule_id.value == "GC-001"


@pytest.mark.parametrize(
    "text",
    [
        "Sebastian Kurz kündigte Reformen an.",
        "Kurz kündigte Reformen an.",
        "DR. KURZ kündigte Reformen an.",
        "S. Kurz kündigte Reformen an.",
    ],
)
def test_unadorned_person_names_are_never_accepted(text: str) -> None:
    store = InMemoryViolationStore()
    result = asyncio.run(
        _guard(store).execute(
            EnforceInstitutionOnlyOutputRequest(
                text=text,
                speaker_kind=SpeakerKind.INSTITUTION,
                invocation_id=InvocationId("inv_name"),
            )
        )
    )

    assert result.decision is not GuardDecision.ACCEPT


def test_institution_only_statement_is_accepted() -> None:
    store = InMemoryViolationStore()
    result = asyncio.run(
        _guard(store).execute(
            EnforceInstitutionOnlyOutputRequest(
                text="Das BMSGPK begrüßt die Reform.",
                speaker_kind=SpeakerKind.INSTITUTION,
                invocation_id=InvocationId("inv_2"),
            )
        )
    )

    assert result.decision is GuardDecision.ACCEPT
    assert result.violations == ()
    assert asyncio.run(store.list()) == ()
