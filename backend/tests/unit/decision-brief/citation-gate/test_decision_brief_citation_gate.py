"""Contract freeze: citation gate (issue #331, implements #340).

Resolution state travels with the citation; the resolver port and its result DTO are frozen.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.application.dto import CitationResolution
from decision_brief.application.ports import CitationResolver
from decision_brief.domain.errors import UnresolvedCitation
from decision_brief.domain.values import (
    CitationProvenance,
    CitationReference,
    PassageId,
)

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
