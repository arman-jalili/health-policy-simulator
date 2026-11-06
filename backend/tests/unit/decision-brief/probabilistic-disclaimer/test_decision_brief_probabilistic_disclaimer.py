"""Contract freeze and JSON rendering (issue #331, implements #344).

The brief JSON always carries the disclaimer and the model/prompt version reference (AC 10).
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    SECTION_ORDINAL,
    BriefId,
    BriefVersion,
    CitationProvenance,
    CitationReference,
    CitedStatement,
    EvidenceStatus,
    OutcomeKind,
    PassageId,
    RunId,
    SectionKind,
    SimulationDisclaimer,
    TopicOutcome,
)
from decision_brief.interfaces.http.schemas import (
    BriefResponse,
    BriefVersionBody,
    DisclaimerBody,
)
from decision_brief.interfaces.renderer import (
    BRIEF_DOCUMENT_SCHEMA_VERSION,
    BriefRenderer,
    JsonBriefRenderer,
    brief_document,
)


def test_the_document_schema_is_versioned() -> None:
    assert BRIEF_DOCUMENT_SCHEMA_VERSION == "1.0"


def test_the_disclaimer_body_carries_the_generation_reference() -> None:
    assert list(DisclaimerBody.model_fields) == ["text", "model_reference", "prompt_version"]
    assert DisclaimerBody.model_fields["text"].is_required()
    assert DisclaimerBody.model_fields["model_reference"].is_required()
    assert DisclaimerBody.model_fields["prompt_version"].is_required()


def test_the_brief_document_always_exposes_disclaimer_and_version() -> None:
    fields = list(BriefResponse.model_fields)
    assert "disclaimer" in fields
    assert "version" in fields
    assert "schema_version" in fields
    assert BriefResponse.model_fields["disclaimer"].is_required()
    assert BriefResponse.model_fields["schema_version"].default == BRIEF_DOCUMENT_SCHEMA_VERSION


def test_the_published_version_identifies_the_run_snapshot_and_generation_time() -> None:
    assert list(BriefVersionBody.model_fields) == [
        "number",
        "run_id",
        "snapshot_ref",
        "generated_at",
        "previous_version",
        "reason",
    ]


def test_the_renderer_is_a_strategy_over_the_artefact() -> None:
    assert hasattr(BriefRenderer, "render")
    assert JsonBriefRenderer.media_type == "application/json"
    assert JsonBriefRenderer().media_type == "application/json"


# ── The rendered document carries the disclosure and the version reference (#344) ───

DISCLAIMER = SimulationDisclaimer(
    text=DEFAULT_DISCLAIMER_TEXT,
    model_reference="openai/gpt-5.1",
    prompt_version="brief.v3",
)


def _statement() -> CitedStatement:
    return CitedStatement(
        text="Waiting times rose by 12%.",
        status=EvidenceStatus.EVIDENCED,
        citations=(
            CitationReference(
                passage_id=PassageId("psg_01J"),
                provenance=CitationProvenance(
                    outlet="Der Standard",
                    published_on=date(2026, 1, 2),
                    medium="print",
                    page_from=3,
                    page_to=4,
                    source_uri="https://example.test/a",
                ),
                quote="Waiting times rose by 12% in 2025.",
            ),
        ),
        claim_ids=("clm_01J",),
    )


def _brief() -> DecisionBrief:
    return DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
        ),
        sections={
            kind: BriefSection(
                kind=kind,
                ordinal=SECTION_ORDINAL[kind],
                statements=(_statement(),) if kind is SectionKind.QUESTION else (),
            )
            for kind in reversed(list(SectionKind))
        },
        rejected_proposals=(
            RejectedProposalRecord(
                measure="Single payer fund",
                blocking_stakeholders=("Ärztekammer",),
                reasons=("no constitutional basis",),
            ),
        ),
        outcomes=(
            TopicOutcome(
                topic="Single payer fund",
                kind=OutcomeKind.BLOCKED,
                blocking_stakeholders=("Ärztekammer",),
            ),
        ),
        disclaimer=DISCLAIMER,
    )


def test_the_document_contains_the_disclaimer_and_the_version_reference() -> None:
    document = brief_document(_brief())

    assert document["disclaimer"] == {
        "text": DEFAULT_DISCLAIMER_TEXT,
        "model_reference": "openai/gpt-5.1",
        "prompt_version": "brief.v3",
    }
    assert document["schema_version"] == "1.0"


def test_the_rendered_json_validates_against_the_frozen_response_schema() -> None:
    payload = JsonBriefRenderer().render(_brief())

    model = BriefResponse.model_validate(json.loads(payload))

    assert model.disclaimer.model_reference == "openai/gpt-5.1"
    assert model.disclaimer.prompt_version == "brief.v3"
    assert model.disclaimer.text == DEFAULT_DISCLAIMER_TEXT


def test_the_document_lists_the_eight_sections_in_reading_order() -> None:
    document = brief_document(_brief())

    kinds = [section["kind"] for section in document["sections"]]
    assert kinds == [
        "question_summary",
        "actors_involved",
        "negotiation_history",
        "conflict_analysis",
        "compromise_proposals",
        "consensus_analysis",
        "open_disputes",
        "impact",
    ]


def test_citations_render_with_their_locator_and_resolution_state() -> None:
    document = brief_document(_brief())

    citation = document["sections"][0]["statements"][0]["citations"][0]
    assert citation == {
        "passage_id": "psg_01J",
        "resolved": True,
        "quote": "Waiting times rose by 12% in 2025.",
        "outlet": "Der Standard",
        "published_on": "2026-01-02",
        "medium": "print",
        "page_from": 3,
        "page_to": 4,
        "source_uri": "https://example.test/a",
    }


def test_the_document_states_blocked_outcomes_and_rejected_proposals() -> None:
    document = brief_document(_brief())

    assert document["outcomes"][0]["kind"] == "blocked"
    assert document["outcomes"][0]["blocking_stakeholders"] == ["Ärztekammer"]
    assert document["rejected_proposals"][0]["measure"] == "Single payer fund"


def test_rendering_is_deterministic_and_keeps_non_ascii_readable() -> None:
    renderer = JsonBriefRenderer()

    first = renderer.render(_brief())
    second = renderer.render(_brief())

    assert first == second
    assert b"\xc3\x84rztekammer" in first  # UTF-8, not \u escapes
    assert b"probabilistic" in first


def test_a_successor_document_carries_its_lineage() -> None:
    brief = _brief()
    brief.version = BriefVersion(
        number=2,
        run_id=RunId("run_01J"),
        snapshot_ref="snap_01J",
        generated_at=datetime(2026, 11, 7, tzinfo=UTC),
        previous_version=1,
        reason="corrected impact section",
    )

    document = brief_document(brief)

    assert document["version"]["previous_version"] == 1
    assert document["version"]["reason"] == "corrected impact section"
