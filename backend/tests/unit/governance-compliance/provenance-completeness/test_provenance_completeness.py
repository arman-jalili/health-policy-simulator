"""Provenance disclosure fails when evidence, arguments or invocation are missing."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from governance_compliance.application.commands import DisclosePositionProvenanceRequest
from governance_compliance.application.dto import ProvenanceFacts
from governance_compliance.application.errors import ProvenanceIncomplete
from governance_compliance.application.services import DisclosePositionProvenance
from governance_compliance.application.values import PositionId
from governance_compliance.infrastructure.repository.memory import InMemoryProvenanceStore


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


class _Facts:
    def __init__(self, facts: ProvenanceFacts | None) -> None:
        self._facts = facts

    async def load(self, position_id: PositionId) -> ProvenanceFacts | None:
        return self._facts


def _service(facts: ProvenanceFacts | None) -> DisclosePositionProvenance:
    return DisclosePositionProvenance(
        facts=_Facts(facts),
        store=InMemoryProvenanceStore(),
        clock=_Clock(),
        uow=_Uow(),
    )


def test_complete_facts_produce_a_disclosure() -> None:
    facts = ProvenanceFacts(
        position_id=PositionId("pos_1"),
        evidence_ids=("psg_1",),
        argument_ids=("arg_1",),
        invocation_id="inv_1",
        prompt_version="2",
        model="scripted-local",
    )
    result = asyncio.run(
        _service(facts).execute(DisclosePositionProvenanceRequest(position_id=PositionId("pos_1")))
    )

    assert result.record.invocation_id == "inv_1"
    assert result.record.evidence_ids == ("psg_1",)
    assert result.record.version == 1


@pytest.mark.parametrize("missing", ["evidence", "arguments", "invocation", "model"])
def test_incomplete_facts_fail_closed(missing: str) -> None:
    facts = ProvenanceFacts(
        position_id=PositionId("pos_1"),
        evidence_ids=() if missing == "evidence" else ("psg_1",),
        argument_ids=() if missing == "arguments" else ("arg_1",),
        invocation_id=None if missing == "invocation" else "inv_1",
        prompt_version="2",
        model=None if missing == "model" else "scripted-local",
    )

    with pytest.raises(ProvenanceIncomplete):
        asyncio.run(
            _service(facts).execute(
                DisclosePositionProvenanceRequest(position_id=PositionId("pos_1"))
            )
        )
