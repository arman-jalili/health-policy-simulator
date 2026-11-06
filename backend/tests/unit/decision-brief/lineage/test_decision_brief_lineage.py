"""Contract freeze and version lineage (issue #331, implements #341).

Version N+1 references N and states a reason; N stays retrievable unchanged.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.application.commands import VersionDecisionBriefRequest
from decision_brief.application.dto import BriefResult
from decision_brief.application.services import VersionDecisionBrief
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import (
    BriefNotFound,
    BriefNotPublished,
    BriefVersionConflict,
    PublishedBriefIsImmutable,
)
from decision_brief.domain.events import DecisionBriefPublished, DecisionBriefVersioned
from decision_brief.domain.repositories import DecisionBriefRepository
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    SECTION_ORDINAL,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitedStatement,
    EvidenceStatus,
    RunId,
    SectionKind,
    SimulationDisclaimer,
)


def test_brief_version_carries_lineage_fields() -> None:
    assert field_names(BriefVersion) == [
        "number",
        "run_id",
        "snapshot_ref",
        "generated_at",
        "previous_version",
        "reason",
    ]


def test_version_request_requires_a_reason() -> None:
    assert field_names(VersionDecisionBriefRequest) == ["brief_id", "reason", "requested_by"]


def test_versioning_event_payload_is_frozen() -> None:
    assert field_names(DecisionBriefVersioned) == ["brief_id", "previous_version", "reason"]
    assert DecisionBriefVersioned.name == "DecisionBriefVersioned"


def test_the_repository_lists_all_versions_of_a_run() -> None:
    assert parameter_names(DecisionBriefRepository.versions_for_run) == ["self", "run_id"]


def test_versioning_service_names_its_collaborators() -> None:
    service = VersionDecisionBrief(
        briefs=None,  # type: ignore[arg-type]
        events=None,  # type: ignore[arg-type]
        clock=None,  # type: ignore[arg-type]
        ids=None,  # type: ignore[arg-type]
        uow=None,  # type: ignore[arg-type]
    )
    assert len(service.collaborators()) == 5
    assert "execute" in dir(service)


def test_supersede_by_takes_the_reason_as_keyword_only() -> None:
    assert parameter_names(DecisionBrief.supersede_by) == ["self", "successor", "reason"]


# ── Version N+1 references N and states a reason (#341) ─────────────────────────────

DISCLAIMER = SimulationDisclaimer(
    text=DEFAULT_DISCLAIMER_TEXT,
    model_reference="openai/gpt-5.1",
    prompt_version="brief.v3",
)


def _published(number: int = 1, run: str = "run_01J") -> DecisionBrief:
    statement = CitedStatement(text="Waiting times rose.", status=EvidenceStatus.NARRATIVE)
    brief = DecisionBrief(
        id=BriefId(f"brf_0{number}J"),
        run_id=RunId(run),
        version=BriefVersion(
            number=number,
            run_id=RunId(run),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections={
            kind: BriefSection(
                kind=kind,
                ordinal=SECTION_ORDINAL[kind],
                statements=(statement,) if kind is SectionKind.QUESTION else (),
            )
            for kind in SectionKind
        },
        disclaimer=DISCLAIMER,
    )
    brief.publish()
    return brief


def _successor(prior: DecisionBrief, *, number: int, previous: int, reason: str) -> DecisionBrief:
    return DecisionBrief(
        id=BriefId(f"brf_0{number}J"),
        run_id=prior.run_id,
        version=BriefVersion(
            number=number,
            run_id=prior.run_id,
            snapshot_ref=prior.version.snapshot_ref,
            generated_at=datetime(2026, 11, 7, tzinfo=UTC),
            previous_version=previous,
            reason=reason,
        ),
        sections=dict(prior.sections),
        disclaimer=DISCLAIMER,
    )


class FakeBriefs:
    def __init__(self, *briefs: DecisionBrief) -> None:
        self._items = {str(brief.id): brief for brief in briefs}

    async def get(self, brief_id: BriefId) -> DecisionBrief | None:
        return self._items.get(str(brief_id))

    async def save(self, brief: DecisionBrief) -> None:
        self._items[str(brief.id)] = brief

    async def versions_for_run(self, run_id: RunId) -> list[DecisionBrief]:
        return sorted(
            (b for b in self._items.values() if b.run_id == run_id),
            key=lambda b: b.version.number,
        )


class FakeEvents:
    def __init__(self) -> None:
        self.published: list[Any] = []

    async def publish(self, events: Any, *, trace_id: str | None = None) -> None:
        self.published.extend(events)


class FakeUow:
    @asynccontextmanager
    async def transaction(self) -> Any:
        yield None


class FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


class FakeIds:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_NEW"


def _service(briefs: FakeBriefs, events: FakeEvents) -> VersionDecisionBrief:
    return VersionDecisionBrief(
        briefs=briefs,
        events=events,
        clock=FakeClock(),
        ids=FakeIds(),
        uow=FakeUow(),
    )


def test_superseding_moves_the_prior_to_superseded_and_returns_n_plus_one() -> None:
    prior = _published()
    successor = _successor(prior, number=2, previous=1, reason="corrected impact section")

    returned = prior.supersede_by(successor, reason="corrected impact section")

    assert returned is successor
    assert prior.status is BriefStatus.SUPERSEDED
    assert prior.events[-1] == DecisionBriefVersioned(
        BriefId("brf_02J"), 1, "corrected impact section"
    )


def test_the_prior_version_stays_readable_and_immutable_after_superseding() -> None:
    prior = _published()
    successor = _successor(prior, number=2, previous=1, reason="correction")

    prior.supersede_by(successor, reason="correction")

    assert len(prior.sections) == 8
    with pytest.raises(PublishedBriefIsImmutable):
        prior.sections.clear()


def test_a_draft_cannot_be_superseded() -> None:
    draft = _published()
    draft = DecisionBrief(
        id=BriefId("brf_09J"),
        run_id=draft.run_id,
        version=BriefVersion(
            number=1,
            run_id=draft.run_id,
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections=dict(draft.sections),
        disclaimer=DISCLAIMER,
    )
    successor = _successor(draft, number=2, previous=1, reason="correction")

    with pytest.raises(BriefNotPublished):
        draft.supersede_by(successor, reason="correction")


@pytest.mark.parametrize(
    ("number", "previous", "reason"),
    [(3, 1, "correction"), (2, 1, "other reason")],
)
def test_a_successor_must_be_n_plus_one_referencing_n_with_the_same_reason(
    number: int, previous: int, reason: str
) -> None:
    prior = _published()
    successor = _successor(prior, number=number, previous=previous, reason=reason)

    with pytest.raises(BriefVersionConflict):
        prior.supersede_by(successor, reason="correction")


def test_a_version_cannot_reference_itself() -> None:
    prior = _published()

    with pytest.raises(ValueError, match="earlier version"):
        _successor(prior, number=2, previous=2, reason="correction")


def test_a_successor_of_another_run_is_refused() -> None:
    prior = _published()
    other_run = _published(run="run_99J")
    successor = _successor(other_run, number=2, previous=1, reason="correction")

    with pytest.raises(BriefVersionConflict):
        prior.supersede_by(successor, reason="correction")


async def test_version_decision_brief_publishes_n_plus_one_and_records_the_transaction() -> None:
    prior = _published()
    briefs = FakeBriefs(prior)
    events = FakeEvents()

    result: BriefResult = await _service(briefs, events).execute(
        VersionDecisionBriefRequest(brief_id=prior.id, reason="corrected impact section")
    )

    successor = result.brief
    assert successor.version.number == 2
    assert successor.version.previous_version == 1
    assert successor.version.reason == "corrected impact section"
    assert successor.status is BriefStatus.PUBLISHED
    assert prior.status is BriefStatus.SUPERSEDED
    assert await briefs.get(BriefId("brf_NEW")) is successor
    assert isinstance(events.published[0], DecisionBriefVersioned)
    assert isinstance(events.published[-1], DecisionBriefPublished)


async def test_versioning_requires_a_reason() -> None:
    prior = _published()
    with pytest.raises(ValueError, match="requires a reason"):
        await _service(FakeBriefs(prior), FakeEvents()).execute(
            VersionDecisionBriefRequest(brief_id=prior.id, reason="  ")
        )


async def test_versioning_an_unknown_brief_is_a_not_found() -> None:
    with pytest.raises(BriefNotFound):
        await _service(FakeBriefs(), FakeEvents()).execute(
            VersionDecisionBriefRequest(brief_id=BriefId("brf_missing"), reason="correction")
        )


async def test_versioning_a_draft_is_refused() -> None:
    prior = _published()
    draft = DecisionBrief(
        id=BriefId("brf_09J"),
        run_id=prior.run_id,
        version=BriefVersion(
            number=1,
            run_id=prior.run_id,
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections=dict(prior.sections),
        disclaimer=DISCLAIMER,
    )
    with pytest.raises(BriefNotPublished):
        await _service(FakeBriefs(draft), FakeEvents()).execute(
            VersionDecisionBriefRequest(brief_id=draft.id, reason="correction")
        )
