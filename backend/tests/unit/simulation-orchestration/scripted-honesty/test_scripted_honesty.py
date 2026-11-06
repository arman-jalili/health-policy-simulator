"""Contract: the scripted provider is explainable, not prompt theatre (#429)."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_orchestration.application.errors import LlmOutputUnparseable
from simulation_orchestration.application.values import NegotiationTurnBriefing
from simulation_orchestration.infrastructure.negotiation_nodes import _decision


def _briefing(**overrides: object) -> NegotiationTurnBriefing:
    values: dict[str, object] = {
        "persona_name": "Österreichische Gesundheitskasse",
        "topic": "Kassenstellen aufstocken",
        "evidence_pack_id": "pack_1",
        "passage_ids": ("psg_1",),
        "previous_learning": "",
        "current_stances": "",
        "institution_code": "oegk",
        "interests": ("waiting_times: Shorten elective waiting times",),
        "interest_weights": (1.0,),
        "constraints": ("No increase in contribution rates",),
        "red_lines": ("Closure of regional hospitals",),
        "veto_classes": ("statutory_benefit_change",),
    }
    values.update(overrides)
    return NegotiationTurnBriefing(**values)  # type: ignore[arg-type]


def test_scripted_prompt_echo_never_becomes_the_persisted_argument() -> None:
    prompt = "[stakeholder-turn@1] Persona: ÖGK. Agenda topic: Kassenstellen aufstocken."

    decision = _decision(prompt, _briefing(), synthetic=True, prompt=prompt)

    assert prompt not in decision.argument
    assert decision.argument.startswith("[synthetic]")
    assert "Begründung" in decision.argument
    assert decision.stance == "support"
    assert decision.claims == ()


def test_scripted_stance_is_explained_by_the_persona_card() -> None:
    briefing = _briefing(
        interest_weights=(0.9,),
        veto_classes=("fee_schedule",),
    )

    decision = _decision("echo", briefing, synthetic=True, prompt="echo")

    assert decision.stance == "conditional_accept"
    assert "veto" in decision.argument
    assert "fee_schedule" in decision.argument


def test_unparseable_real_provider_output_fails_with_a_named_code() -> None:
    with pytest.raises(LlmOutputUnparseable) as caught:
        _decision("I think this is good.", _briefing(), synthetic=False, prompt="p")

    assert caught.value.code == "LLM_OUTPUT_UNPARSEABLE"


def test_node_and_acl_do_not_derive_a_stance_from_an_actor_hash() -> None:
    root = Path(__file__).resolve().parents[4] / "src" / "simulation_orchestration"
    for relative in (
        "infrastructure/negotiation_nodes.py",
        "infrastructure/negotiation_session.py",
    ):
        source = (root / relative).read_text(encoding="utf-8")
        assert "hashlib" not in source
        assert "sha256(actor" not in source
        assert "_fallback_stance" not in source
