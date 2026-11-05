"""The rule chain aggregates every violation and honours severity."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from governance_compliance.application.commands import EnforceInstitutionOnlyOutputRequest
from governance_compliance.application.rules import (
    GuardRuleChain,
    PersonalQuotationRule,
    PersonReferenceRule,
    UnsupportedFactRule,
)
from governance_compliance.application.services import EnforceInstitutionOnlyOutput
from governance_compliance.application.values import (
    GuardDecision,
    InstitutionalAllowlist,
    InvocationId,
    RunId,
    SpeakerKind,
)
from governance_compliance.infrastructure.ner import RegexPersonNameDetector
from governance_compliance.infrastructure.repository.memory import InMemoryViolationStore


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
        rules=GuardRuleChain(
            [
                PersonReferenceRule(detector),
                PersonalQuotationRule(detector),
                UnsupportedFactRule(),
            ]
        ),
        allowlist=InstitutionalAllowlist(),
        violations=store,
        clock=_Clock(),
        uow=_Uow(),
    )


def test_rewrite_does_not_mask_reject_and_each_rule_writes_a_row() -> None:
    store = InMemoryViolationStore()
    result = asyncio.run(
        _guard(store).execute(
            EnforceInstitutionOnlyOutputRequest(
                text='Dr. Kurz sagte: "Die Kosten steigen 2026 um 5 Prozent."',
                speaker_kind=SpeakerKind.INSTITUTION,
                invocation_id=InvocationId("inv_multi"),
                run_id=RunId("run_multi"),
            )
        )
    )

    assert result.decision is GuardDecision.REJECT
    assert len(result.violations) == 3
    assert {item.rule_id.value for item in result.violations} == {"GC-001", "GC-002", "GC-004"}


def test_hash_includes_the_full_text_for_distinct_calls() -> None:
    first = asyncio.run(
        _guard(InMemoryViolationStore()).execute(
            EnforceInstitutionOnlyOutputRequest(
                text="Dr. Kurz sagte es.",
                speaker_kind=SpeakerKind.INSTITUTION,
                invocation_id=InvocationId("inv_same"),
            )
        )
    )
    second = asyncio.run(
        _guard(InMemoryViolationStore()).execute(
            EnforceInstitutionOnlyOutputRequest(
                text="Dr. Kurz sagte etwas anderes.",
                speaker_kind=SpeakerKind.INSTITUTION,
                invocation_id=InvocationId("inv_same"),
            )
        )
    )

    assert first.violations[0].violation_hash != second.violations[0].violation_hash
