"""Contract freeze: ``DecisionBrief`` aggregate surface (issue #331, implements #336).

The generated placeholder used hyphenated identifiers and could not be imported. These checks assert
the frozen aggregate instead: field order, draft defaults, gate predicates and gating methods.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import field_names, method_names, parameter_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.errors import (
    DisclosureMissing,
    IncompleteBrief,
    PublishedBriefIsImmutable,
    StatementWithoutCitation,
    UnresolvedCitation,
)
from decision_brief.domain.events import (
    BriefBlockedByMissingDisclosure,
    CitationResolutionFailed,
    DecisionBriefPublished,
)
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    SECTION_ORDINAL,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitationProvenance,
    CitationReference,
    CitedStatement,
    EvidenceStatus,
    PassageId,
    RunId,
    SectionKind,
    SimulationDisclaimer,
)

VERSION = BriefVersion(
    number=1,
    run_id=RunId("run_01J"),
    snapshot_ref="snap_01J",
    generated_at=datetime(2026, 11, 6, tzinfo=UTC),
)


def _brief(sections: dict[SectionKind, BriefSection]) -> DecisionBrief:
    return DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=VERSION,
        sections=sections,
    )


def _resolved(passage_id: str) -> CitationReference:
    return CitationReference(
        passage_id=PassageId(passage_id),
        provenance=CitationProvenance(
            outlet="Der Standard",
            published_on=datetime(2026, 1, 2, tzinfo=UTC).date(),
            medium="print",
            page_from=1,
            page_to=2,
            source_uri="https://example.test/a",
        ),
    )


def test_aggregate_fields_are_frozen() -> None:
    assert field_names(DecisionBrief) == [
        "id",
        "run_id",
        "version",
        "sections",
        "rejected_proposals",
        "disclaimer",
        "outcomes",
        "status",
        "events",
    ]


def test_a_new_brief_is_a_draft_with_no_events() -> None:
    brief = _brief({})
    assert brief.status is BriefStatus.DRAFT
    assert brief.events == []
    assert brief.rejected_proposals == ()
    assert brief.disclaimer is None
    assert brief.is_published() is False


def test_missing_sections_names_the_absent_kind() -> None:
    present = [kind for kind in SectionKind if kind is not SectionKind.IMPACT]
    brief = _brief(
        {
            kind: BriefSection(kind=kind, ordinal=ordinal)
            for ordinal, kind in enumerate(present, start=1)
        }
    )
    assert brief.missing_sections() == frozenset({SectionKind.IMPACT})


def test_missing_sections_is_empty_for_all_eight() -> None:
    brief = _brief(
        {
            kind: BriefSection(kind=kind, ordinal=ordinal)
            for ordinal, kind in enumerate(SectionKind, start=1)
        }
    )
    assert brief.missing_sections() == frozenset()


def test_unresolved_citations_collects_only_unresolved_ones() -> None:
    statement = CitedStatement(
        text="Waiting times rose by 12%.",
        status=EvidenceStatus.EVIDENCED,
        citations=(
            _resolved("psg_01J"),
            CitationReference(passage_id=PassageId("psg_02J")),
        ),
    )
    brief = _brief(
        {
            SectionKind.QUESTION: BriefSection(
                kind=SectionKind.QUESTION, ordinal=1, statements=(statement,)
            )
        }
    )
    unresolved = brief.unresolved_citations()
    assert [str(item.passage_id) for item in unresolved] == ["psg_02J"]


def test_gating_surface_is_frozen() -> None:
    assert {
        "publish",
        "assert_statement_evidence",
        "assert_immutable",
        "assert_rejected_proposals_disclosed",
        "supersede_by",
        "missing_sections",
        "unresolved_citations",
        "is_published",
    } <= method_names(DecisionBrief)


def test_publishing_an_empty_brief_reports_every_missing_section() -> None:
    brief = _brief({})
    with pytest.raises(IncompleteBrief) as raised:
        brief.publish()
    assert len(raised.value.missing) == 8


def test_supersede_by_requires_a_reason() -> None:
    assert parameter_names(DecisionBrief.supersede_by) == ["self", "successor", "reason"]


# ── Publication gates (issue #332) ────────────────────────────────────────────────

DISCLAIMER = SimulationDisclaimer(
    text=DEFAULT_DISCLAIMER_TEXT,
    model_reference="openai/gpt-5.1",
    prompt_version="brief.v3",
)


def _sections(
    statements: dict[SectionKind, tuple[CitedStatement, ...]] | None = None,
    kinds: Sequence[SectionKind] | None = None,
) -> dict[SectionKind, BriefSection]:
    statements = statements or {}
    selected = list(kinds) if kinds is not None else list(SectionKind)
    return {
        kind: BriefSection(
            kind=kind,
            ordinal=SECTION_ORDINAL[kind],
            statements=statements.get(kind, ()),
        )
        for kind in selected
    }


def _ready(**overrides: object) -> DecisionBrief:
    fields: dict[str, object] = {
        "id": BriefId("brf_01J"),
        "run_id": RunId("run_01J"),
        "version": VERSION,
        "sections": _sections(),
        "disclaimer": DISCLAIMER,
    }
    fields.update(overrides)
    return DecisionBrief(**fields)  # type: ignore[arg-type]


def test_publishing_with_seven_sections_names_the_missing_kind() -> None:
    seven = [kind for kind in SectionKind if kind is not SectionKind.IMPACT]
    brief = _ready(sections=_sections(kinds=seven))

    with pytest.raises(IncompleteBrief) as raised:
        brief.publish()

    assert raised.value.missing == ("impact",)
    assert brief.status is BriefStatus.BLOCKED
    assert brief.events == []
    assert brief.is_published() is False


def test_an_unresolved_citation_blocks_publication_and_is_recorded() -> None:
    statement = CitedStatement(
        text="Waiting times rose by 12%.",
        status=EvidenceStatus.EVIDENCED,
        citations=(_resolved("psg_01J"), CitationReference(passage_id=PassageId("psg_02J"))),
    )
    brief = _ready(sections=_sections({SectionKind.QUESTION: (statement,)}))

    with pytest.raises(UnresolvedCitation) as raised:
        brief.publish()

    assert raised.value.passage_id == "psg_02J"
    assert brief.events == [CitationResolutionFailed(BriefId("brf_01J"), 1, PassageId("psg_02J"))]
    assert brief.status is BriefStatus.BLOCKED
    assert brief.is_published() is False


def test_a_statement_evidenced_without_a_citation_blocks_publication() -> None:
    statement = CitedStatement(text="Beds fell by 3%.", status=EvidenceStatus.EVIDENCED)
    brief = _ready(sections=_sections({SectionKind.IMPACT: (statement,)}))

    with pytest.raises(StatementWithoutCitation):
        brief.publish()

    assert brief.status is BriefStatus.BLOCKED


def test_narrative_statements_may_publish_without_citations() -> None:
    statement = CitedStatement(text="The mood was tense.", status=EvidenceStatus.NARRATIVE)
    brief = _ready(sections=_sections({SectionKind.HISTORY: (statement,)}))

    brief.publish()

    assert brief.is_published() is True


def test_a_brief_without_a_disclaimer_cannot_publish() -> None:
    brief = _ready(disclaimer=None)

    with pytest.raises(DisclosureMissing) as raised:
        brief.publish()

    assert raised.value.missing == "simulation_disclaimer"
    assert brief.events == [
        BriefBlockedByMissingDisclosure(BriefId("brf_01J"), ("simulation_disclaimer",))
    ]
    assert brief.status is BriefStatus.BLOCKED


def test_a_complete_brief_publishes_and_records_the_event() -> None:
    statement = CitedStatement(
        text="Waiting times rose by 12%.",
        status=EvidenceStatus.EVIDENCED,
        citations=(_resolved("psg_01J"),),
    )
    brief = _ready(sections=_sections({SectionKind.QUESTION: (statement,)}))

    brief.publish()

    assert brief.is_published() is True
    assert brief.events == [DecisionBriefPublished(BriefId("brf_01J"), RunId("run_01J"), 1, 8, 1)]


def test_a_published_brief_cannot_be_published_again() -> None:
    brief = _ready()
    brief.publish()

    with pytest.raises(PublishedBriefIsImmutable):
        brief.publish()


def test_a_rejected_proposal_recorded_in_the_run_must_be_disclosed() -> None:
    brief = _ready()

    with pytest.raises(DisclosureMissing) as raised:
        brief.assert_rejected_proposals_disclosed(["Single payer fund"])

    assert raised.value.missing == "rejected_proposals"
    assert brief.events == [
        BriefBlockedByMissingDisclosure(BriefId("brf_01J"), ("rejected_proposals",))
    ]


def test_disclosing_the_run_rejections_passes_the_gate() -> None:
    brief = _ready(
        rejected_proposals=(
            RejectedProposalRecord(
                measure="Single payer fund",
                blocking_stakeholders=("Ärztekammer",),
                reasons=("no constitutional basis",),
            ),
        )
    )

    brief.assert_rejected_proposals_disclosed(["Single payer fund"])

    assert brief.events == []


def test_a_run_without_rejections_needs_no_disclosure() -> None:
    brief = _ready()

    brief.assert_rejected_proposals_disclosed([])

    assert brief.events == []
