"""Contract freeze: contradiction findings and detector (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import field_names, parameter_names

from claim_validation.domain.entities import ContradictionFinding
from claim_validation.domain.events import ContradictionDetected
from claim_validation.domain.services import ContradictionDetector


def test_finding_links_two_claims_with_delta() -> None:
    assert field_names(ContradictionFinding) == [
        "id",
        "claim_id_a",
        "claim_id_b",
        "measure",
        "delta",
    ]
    assert field_names(ContradictionDetected) == [
        "claim_id_a",
        "claim_id_b",
        "measure",
        "delta",
    ]


def test_detector_requires_both_values_and_the_band() -> None:
    assert parameter_names(ContradictionDetector.is_contradiction) == [
        "self",
        "a",
        "b",
        "band",
    ]


# --- behaviour: finding across two verified claims (issue #172) ------------------------------

from datetime import date  # noqa: E402
from decimal import Decimal  # noqa: E402

from claim_validation.domain.claim import Claim  # noqa: E402
from claim_validation.domain.values import (  # noqa: E402
    ClaimId,
    ClaimType,
    MeasureReference,
    ReferenceFigure,
    ToleranceBand,
    VerificationEvidence,
    VerificationPath,
    VerificationVerdict,
)
from evidence_corpus.domain.values import AuthorityTier  # noqa: E402


def _measure() -> MeasureReference:
    return MeasureReference("Kassenstellen", "count", "2026", "AT")


def _reference() -> ReferenceFigure:
    return ReferenceFigure(
        id="fig_1",  # type: ignore[arg-type]
        measure=_measure(),
        value=Decimal("3.2"),
        tier=AuthorityTier.OFFICIAL_STATISTICS,
        as_of=date(2026, 1, 1),
        source_id="src_1",
    )


def _verified(claim_id: str, value: str) -> Claim:
    claim = Claim(
        id=ClaimId(claim_id),
        text=f"{value} Mrd",
        type=ClaimType.QUANTITATIVE,
        measure=_measure(),
    )
    claim.verify(
        VerificationPath.QUANTITATIVE,
        VerificationEvidence(
            asserted_value=Decimal(value),
            asserted_measure=_measure(),
            reference_figure=_reference(),
        ),
    )
    assert claim.verdict is VerificationVerdict.CONTRADICTED
    return claim


def test_two_claims_for_the_same_measure_produce_a_finding() -> None:
    first = _verified("clm_a", "4.1")
    second = _verified("clm_b", "5.0")

    finding = ContradictionDetector().finding_for(first, second, ToleranceBand())

    assert finding is not None
    assert finding.claim_id_a == "clm_a"
    assert finding.claim_id_b == "clm_b"
    assert finding.delta == Decimal("0.9")


def test_different_measures_never_collapse_into_a_finding() -> None:
    first = _verified("clm_a", "4.1")
    second = _verified("clm_b", "4.1")
    second.measure = MeasureReference("Wartezeit", "days", "2026", "AT")

    assert ContradictionDetector().finding_for(first, second, ToleranceBand()) is None


# --- fix #201: deterministic id makes repeated recording idempotent --------------------------

from claim_validation.infrastructure.repository.memory import (  # noqa: E402
    InMemoryContradictionRepository,
)


def test_same_pair_produces_a_stable_finding_id() -> None:
    first = _verified("clm_a", "4.1")
    second = _verified("clm_b", "5.0")

    one = ContradictionDetector().finding_for(first, second, ToleranceBand())
    two = ContradictionDetector().finding_for(first, second, ToleranceBand())

    assert one is not None
    assert two is not None
    assert one.id == two.id


async def test_recording_the_same_finding_twice_upserts() -> None:
    first = _verified("clm_a", "4.1")
    second = _verified("clm_b", "5.0")
    finding = ContradictionDetector().finding_for(first, second, ToleranceBand())
    assert finding is not None
    repository = InMemoryContradictionRepository()

    await repository.save(finding)

    assert len(await repository.list_all()) == 1
