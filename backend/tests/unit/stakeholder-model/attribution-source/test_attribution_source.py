"""Attribution is classified from the cited corpus passage, not the request body."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Offsets, SpeakerKind
from stakeholder_model.application.commands import RecordHistoricalPositionRequest
from stakeholder_model.application.dto import HistoricalPositionResult
from stakeholder_model.application.services import RecordHistoricalPosition
from stakeholder_model.domain.services import CorpusAttributionRule
from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import AttributionStrength, PassageId
from stakeholder_model.infrastructure.personas import PersonaFactory
from stakeholder_model.infrastructure.repository.memory import InMemoryStakeholderRepository


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


class _Corpus:
    def __init__(self, passages: list[PassageView]) -> None:
        self._passages = passages

    async def passages_about(self, identity: object) -> list[PassageView]:
        return self._passages


def _passage(passage_id: str, text: str, speaker_kind: SpeakerKind) -> PassageView:
    return PassageView(
        passage_id=passage_id,
        article_id="art_1",
        document_id="doc_1",
        text=text,
        provenance=ProvenanceView(
            outlet="Test",
            published_on=date(2026, 1, 1),
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, len(text)),
            source_uri="https://example.test",
        ),
        speaker_kind=speaker_kind,
        citable=True,
    )


def _service(passages: list[PassageView], stakeholder: Stakeholder) -> RecordHistoricalPosition:
    repository = InMemoryStakeholderRepository([stakeholder])
    return RecordHistoricalPosition(
        repository=repository,
        corpus=_Corpus(passages),
        attribution_rule=CorpusAttributionRule(),
        unit_of_work=_Uow(),
        clock=_Clock(),
    )


def _record(
    service: RecordHistoricalPosition, stakeholder: Stakeholder, passage_id: str
) -> HistoricalPositionResult:
    return asyncio.run(
        service.execute(
            RecordHistoricalPositionRequest(
                stakeholder_id=stakeholder.id,
                stance="supports the reform",
                attribution=AttributionStrength.EXPLICIT,
                stated_on=date(2026, 1, 1),
                passage_id=PassageId(passage_id),
            )
        )
    )


def test_named_institution_passage_is_explicit() -> None:
    stakeholder = PersonaFactory().load_all()[0]
    passage = _passage(
        "psg_explicit",
        f"{stakeholder.identity.name} unterstützt die Reform.",
        SpeakerKind.INSTITUTION,
    )

    result = _record(_service([passage], stakeholder), stakeholder, "psg_explicit")

    assert result.attribution is AttributionStrength.EXPLICIT
    assert result.usable is True


def test_person_passage_is_only_reported_even_when_client_says_explicit() -> None:
    stakeholder = PersonaFactory().load_all()[0]
    passage = _passage("psg_person", "Ein Sprecher sagte, die Reform sei gut.", SpeakerKind.PERSON)

    result = _record(_service([passage], stakeholder), stakeholder, "psg_person")

    assert result.attribution is AttributionStrength.REPORTED
    assert result.usable is False


def test_unresolvable_passage_falls_back_to_mention() -> None:
    stakeholder = PersonaFactory().load_all()[0]

    result = _record(_service([], stakeholder), stakeholder, "psg_missing")

    assert result.attribution is AttributionStrength.MENTION
    assert result.usable is False
