"""Contract freeze: ``DecisionBrief`` aggregate surface (issue #331, implements #336).

The generated placeholder used hyphenated identifiers and could not be imported. These checks assert
the frozen aggregate instead: field order, draft defaults, gate predicates and gating methods.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import field_names, method_names, parameter_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.values import (
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


def test_gating_methods_are_frozen_and_still_stubs() -> None:
    assert {
        "publish",
        "assert_statement_evidence",
        "assert_immutable",
        "supersede_by",
        "missing_sections",
        "unresolved_citations",
        "is_published",
    } <= method_names(DecisionBrief)
    brief = _brief({})
    with pytest.raises(NotImplementedError):
        brief.publish()
    with pytest.raises(NotImplementedError):
        brief.assert_immutable()


def test_supersede_by_requires_a_reason() -> None:
    assert parameter_names(DecisionBrief.supersede_by) == ["self", "successor", "reason"]
