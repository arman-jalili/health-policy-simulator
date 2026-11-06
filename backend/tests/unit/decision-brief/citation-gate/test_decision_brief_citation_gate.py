"""Contract freeze: citation gate (issue #331, implements #340).

Resolution state travels with the citation; the resolver port and its result DTO are frozen.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.application.dto import CitationResolution
from decision_brief.application.ports import CitationResolver
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import (
    PublishedBriefIsImmutable,
    UnresolvedCitation,
)
from decision_brief.domain.values import (
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
from decision_brief.infrastructure.acl import EvidenceCorpusCitationResolver
from evidence_corpus.application.commands import ResolvePassageRequest
from evidence_corpus.domain.errors import PassageNotFound
from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Offsets, SourceType, SpeakerKind

PROVENANCE = CitationProvenance(
    outlet="Der Standard",
    published_on=date(2026, 1, 2),
    medium="print",
    page_from=1,
    page_to=2,
    source_uri="https://example.test/a",
)


def test_citation_resolution_dto_is_frozen() -> None:
    assert field_names(CitationResolution) == ["resolved", "unresolved"]


def test_a_citation_without_provenance_is_unresolved() -> None:
    assert CitationReference(passage_id=PassageId("psg_01J")).is_resolved() is False


def test_a_citation_with_provenance_is_resolved() -> None:
    citation = CitationReference(passage_id=PassageId("psg_01J"), provenance=PROVENANCE)
    assert citation.is_resolved() is True


def test_resolution_is_complete_only_when_every_id_resolved() -> None:
    resolved = CitationReference(passage_id=PassageId("psg_01J"), provenance=PROVENANCE)
    assert CitationResolution(resolved=(resolved,)).is_complete is True
    assert CitationResolution(unresolved=(PassageId("psg_02J"),)).is_complete is False


def test_the_resolver_port_takes_passage_ids_and_returns_the_resolution() -> None:
    assert parameter_names(CitationResolver.resolve) == ["self", "passage_ids"]


def test_unresolved_citation_names_brief_and_passage() -> None:
    error = UnresolvedCitation("brf_01J", "psg_02J")
    assert error.code == "UNRESOLVED_CITATION"
    assert error.status_code == 422
    assert error.brief_id == "brf_01J"
    assert error.passage_id == "psg_02J"


def test_provenance_fields_are_the_locator_a_reader_can_open() -> None:
    assert field_names(CitationProvenance) == [
        "outlet",
        "published_on",
        "medium",
        "page_from",
        "page_to",
        "source_uri",
    ]
    assert PROVENANCE.published_on == datetime(2026, 1, 2, tzinfo=UTC).date()


# ── The gate resolves, never invents (#336) ─────────────────────────────────────────


def _passage(passage_id: str) -> PassageView:
    return PassageView(
        passage_id=passage_id,
        article_id="art_01J",
        document_id="doc_01J",
        text="Waiting times rose by 12% in 2025.",
        provenance=ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 1, 2),
            medium="print",
            page_from=3,
            page_to=4,
            offsets=Offsets(10, 48),
            source_uri="https://example.test/a",
        ),
        speaker_kind=SpeakerKind.INSTITUTION,
        citable=True,
        source_type=SourceType.OTHER,
    )


class FakeResolvePassage:
    """The EvidenceCorpus use case, with one unknown passage to prove the fail-closed path."""

    def __init__(self, known: dict[str, PassageView]) -> None:
        self._known = known

    async def execute(self, request: ResolvePassageRequest) -> PassageView:
        view = self._known.get(request.passage_id)
        if view is None:
            raise PassageNotFound(request.passage_id)
        return view


def _brief_with(citations: tuple[CitationReference, ...]) -> DecisionBrief:
    statement = CitedStatement(
        text="Waiting times rose by 12%.",
        status=EvidenceStatus.EVIDENCED,
        citations=citations,
    )
    sections = {
        kind: BriefSection(
            kind=kind,
            ordinal=SECTION_ORDINAL[kind],
            statements=(statement,) if kind is SectionKind.QUESTION else (),
        )
        for kind in SectionKind
    }
    return DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections=sections,
        disclaimer=SimulationDisclaimer(
            text="probabilistic reasoning over a pinned corpus",
            model_reference="openai/gpt-5.1",
            prompt_version="brief.v3",
        ),
    )


async def test_the_resolver_maps_a_passage_to_an_openable_citation() -> None:
    resolver = EvidenceCorpusCitationResolver(FakeResolvePassage({"psg_01J": _passage("psg_01J")}))

    resolution = await resolver.resolve((PassageId("psg_01J"),))

    (citation,) = resolution.resolved
    assert citation.is_resolved() is True
    assert citation.quote == "Waiting times rose by 12% in 2025."
    assert citation.provenance is not None
    assert citation.provenance.outlet == "Der Standard"
    assert citation.provenance.page_from == 3
    assert resolution.unresolved == ()


async def test_the_resolver_reports_a_missing_passage_instead_of_inventing_one() -> None:
    resolver = EvidenceCorpusCitationResolver(FakeResolvePassage({}))

    resolution = await resolver.resolve((PassageId("psg_missing"),))

    assert resolution.resolved == ()
    assert resolution.unresolved == (PassageId("psg_missing"),)
    assert resolution.is_complete is False


async def test_the_resolver_preserves_input_order() -> None:
    resolver = EvidenceCorpusCitationResolver(
        FakeResolvePassage({"psg_01J": _passage("psg_01J"), "psg_02J": _passage("psg_02J")})
    )

    resolution = await resolver.resolve((PassageId("psg_02J"), PassageId("psg_01J")))

    assert [str(c.passage_id) for c in resolution.resolved] == ["psg_02J", "psg_01J"]


async def test_applying_a_resolution_clears_the_gate() -> None:
    brief = _brief_with((CitationReference(passage_id=PassageId("psg_01J")),))
    resolved = CitationReference(
        passage_id=PassageId("psg_01J"),
        provenance=PROVENANCE,
        quote="Waiting times rose by 12% in 2025.",
    )

    brief.resolve_citations((resolved,))
    brief.publish()

    assert brief.unresolved_citations() == ()
    assert brief.status is BriefStatus.PUBLISHED


async def test_a_passage_the_resolver_could_not_resolve_still_blocks_publication() -> None:
    brief = _brief_with(
        (
            CitationReference(passage_id=PassageId("psg_01J")),
            CitationReference(passage_id=PassageId("psg_missing")),
        )
    )
    resolved = CitationReference(passage_id=PassageId("psg_01J"), provenance=PROVENANCE)

    brief.resolve_citations((resolved,))

    with pytest.raises(UnresolvedCitation) as raised:
        brief.publish()
    assert raised.value.passage_id == "psg_missing"
    assert brief.status is BriefStatus.BLOCKED


def test_a_published_brief_rejects_late_citation_work() -> None:
    brief = _brief_with((CitationReference(passage_id=PassageId("psg_01J")),))
    brief.resolve_citations((CitationReference(PassageId("psg_01J"), PROVENANCE),))
    brief.publish()

    with pytest.raises(PublishedBriefIsImmutable):
        brief.resolve_citations(())
