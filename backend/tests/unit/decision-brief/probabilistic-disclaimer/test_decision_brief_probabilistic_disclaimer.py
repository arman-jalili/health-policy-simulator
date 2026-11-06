"""Contract freeze: probabilistic disclaimer in the rendered document (issue #331, implements #348).

The brief JSON always carries the disclaimer and the model/prompt version reference (AC 10).
"""

from __future__ import annotations

from decision_brief.interfaces.http.schemas import (
    BriefResponse,
    BriefVersionBody,
    DisclaimerBody,
)
from decision_brief.interfaces.renderer import (
    BRIEF_DOCUMENT_SCHEMA_VERSION,
    BriefRenderer,
    JsonBriefRenderer,
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
