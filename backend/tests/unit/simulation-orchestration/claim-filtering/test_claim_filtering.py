"""Model-written claims are filtered by the claim agent, never asserted as verified.

NegotiationSession refuses an inadmissible claim outright (correct for API
clients). The orchestrated path asks ClaimValidation first and keeps only admitted
claims, so a model's prose cannot dead-letter a paid run — observed live with a
DeepSeek turn whose claim was `ambiguous`.
"""

from __future__ import annotations

from simulation_orchestration.infrastructure.negotiation_session import NegotiationSessionGateway


def _gateway(admissible: set[str] | None) -> NegotiationSessionGateway:
    async def predicate(text: str) -> bool:
        return admissible is not None and text in admissible

    return NegotiationSessionGateway(
        runs=None,  # type: ignore[arg-type]
        open_round=None,  # type: ignore[arg-type]
        submit_position=None,  # type: ignore[arg-type]
        take_turn=None,  # type: ignore[arg-type]
        close_round=None,  # type: ignore[arg-type]
        evidence_pack_for=None,  # type: ignore[arg-type]
        claim_admissible=None if admissible is None else predicate,
    )


async def test_only_admitted_claims_survive() -> None:
    gateway = _gateway({"Die Kassenstellen wurden 2025 aufgestockt."})

    admitted = await gateway._admissible_claims(
        (
            "Die Kassenstellen wurden 2025 aufgestockt.",
            "Das senkt die Wartezeiten garantiert.",
        )
    )

    assert admitted == ("Die Kassenstellen wurden 2025 aufgestockt.",)


async def test_no_predicate_means_no_claims_not_a_crash() -> None:
    gateway = _gateway(None)

    assert await gateway._admissible_claims(("irgendetwas",)) == ()
    assert await gateway._admissible_claims(()) == ()
