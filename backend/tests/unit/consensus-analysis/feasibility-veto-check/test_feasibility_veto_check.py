"""Contract freeze: feasibility veto check (issue #305, implements #318)."""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.errors import FeasibilityContradictsVeto
from consensus_analysis.domain.events import FeasibilityRated
from consensus_analysis.domain.services import FeasibilityGuard
from consensus_analysis.domain.values import (
    BasisKind,
    EstimateBasis,
    FeasibilityLevel,
    FeasibilityRating,
    PackageId,
    ProposalClass,
    StakeholderId,
)


def test_contradicting_a_veto_is_a_stable_error_code() -> None:
    assert FeasibilityContradictsVeto.code == "FEASIBILITY_CONTRADICTS_VETO"
    assert FeasibilityContradictsVeto.status_code == 409


def test_all_three_dimensions_are_part_of_the_rating() -> None:
    assert field_names(FeasibilityRating) == [
        "political",
        "legal",
        "administrative",
        "basis",
        "blockers",
    ]
    rating = FeasibilityRating(
        political=FeasibilityLevel.MEDIUM,
        legal=FeasibilityLevel.HIGH,
        administrative=FeasibilityLevel.UNKNOWN,
        basis=EstimateBasis(kind=BasisKind.MODELLED),
    )
    assert rating.legal is FeasibilityLevel.HIGH
    assert parameter_names(FeasibilityRating.is_fully_rated) == ["self"]


def test_the_guard_signature_is_frozen() -> None:
    assert parameter_names(FeasibilityGuard.assert_consistent) == [
        "self",
        "rating",
        "consenting",
        "vetoes",
        "proposal_class",
    ]
    rating = FeasibilityRating(
        political=FeasibilityLevel.HIGH,
        legal=FeasibilityLevel.HIGH,
        administrative=FeasibilityLevel.HIGH,
        basis=EstimateBasis(kind=BasisKind.MODELLED),
    )
    FeasibilityGuard().assert_consistent(
        rating=rating,
        consenting=(StakeholderId("stk_bva"),),
        vetoes={},
        proposal_class=ProposalClass.BUDGET_FRAME,
    )

    with pytest.raises(FeasibilityContradictsVeto):
        FeasibilityGuard().assert_consistent(
            rating=rating,
            consenting=(StakeholderId("stk_bva"),),
            vetoes={StakeholderId("stk_bva"): frozenset({ProposalClass.BUDGET_FRAME})},
            proposal_class=ProposalClass.BUDGET_FRAME,
        )


def test_an_unrated_dimension_is_not_a_complete_rating() -> None:
    complete = FeasibilityRating(
        political=FeasibilityLevel.HIGH,
        legal=FeasibilityLevel.HIGH,
        administrative=FeasibilityLevel.HIGH,
        basis=EstimateBasis(kind=BasisKind.MODELLED),
    )
    partial = FeasibilityRating(
        political=FeasibilityLevel.HIGH,
        legal=FeasibilityLevel.HIGH,
        administrative=FeasibilityLevel.UNKNOWN,
        basis=EstimateBasis(kind=BasisKind.MODELLED),
    )
    assert complete.is_fully_rated() is True
    assert partial.is_fully_rated() is False


def test_the_rating_event_names_the_blockers() -> None:
    assert FeasibilityRated.name == "FeasibilityRated"
    assert field_names(FeasibilityRated) == ["package_id", "ratings", "blockers"]
    assert FeasibilityRated(package_id=PackageId("pkg_1"), ratings={}, blockers=()).blockers == ()


# ── issue #318: feasibility cannot be asserted against a blocker ───────────────────────────────


def _rating(
    political: FeasibilityLevel = FeasibilityLevel.HIGH,
    legal: FeasibilityLevel = FeasibilityLevel.HIGH,
    administrative: FeasibilityLevel = FeasibilityLevel.HIGH,
    *,
    blockers: tuple[StakeholderId, ...] = (),
) -> FeasibilityRating:
    return FeasibilityRating(
        political=political,
        legal=legal,
        administrative=administrative,
        basis=EstimateBasis(kind=BasisKind.MODELLED),
        blockers=blockers,
    )


def test_a_feasible_scenario_cannot_name_a_veto_holder_as_consenting() -> None:
    with pytest.raises(FeasibilityContradictsVeto) as raised:
        FeasibilityGuard().assert_consistent(
            rating=_rating(),
            consenting=(StakeholderId("stk_bva"),),
            vetoes={StakeholderId("stk_bva"): frozenset({ProposalClass.BUDGET_FRAME})},
            proposal_class=ProposalClass.BUDGET_FRAME,
        )
    assert raised.value.code == "FEASIBILITY_CONTRADICTS_VETO"
    assert raised.value.holders == ("stk_bva",)
    assert len(raised.value.details) == 1


def test_a_feasible_scenario_may_name_a_non_holder_as_consenting() -> None:
    FeasibilityGuard().assert_consistent(
        rating=_rating(),
        consenting=(StakeholderId("stk_aek"),),
        vetoes={StakeholderId("stk_bva"): frozenset({ProposalClass.BUDGET_FRAME})},
        proposal_class=ProposalClass.BUDGET_FRAME,
    )


def test_an_infeasible_scenario_may_name_whoever_it_likes() -> None:
    """A rating that admits a low dimension asserts nothing, so it contradicts nothing."""
    FeasibilityGuard().assert_consistent(
        rating=_rating(political=FeasibilityLevel.LOW),
        consenting=(StakeholderId("stk_bva"),),
        vetoes={StakeholderId("stk_bva"): frozenset({ProposalClass.BUDGET_FRAME})},
        proposal_class=ProposalClass.BUDGET_FRAME,
    )


def test_an_unrated_dimension_asserts_no_feasibility() -> None:
    FeasibilityGuard().assert_consistent(
        rating=_rating(administrative=FeasibilityLevel.UNKNOWN),
        consenting=(StakeholderId("stk_bva"),),
        vetoes={StakeholderId("stk_bva"): frozenset({ProposalClass.BUDGET_FRAME})},
        proposal_class=ProposalClass.BUDGET_FRAME,
    )


def test_listing_someone_as_blocker_and_consenting_is_contradictory() -> None:
    with pytest.raises(FeasibilityContradictsVeto):
        FeasibilityGuard().assert_consistent(
            rating=_rating(blockers=(StakeholderId("stk_aek"),)),
            consenting=(StakeholderId("stk_aek"),),
            vetoes={},
            proposal_class=ProposalClass.FEE_SCHEDULE,
        )


def test_a_veto_over_another_class_does_not_block_feasibility() -> None:
    FeasibilityGuard().assert_consistent(
        rating=_rating(),
        consenting=(StakeholderId("stk_bva"),),
        vetoes={StakeholderId("stk_bva"): frozenset({ProposalClass.HOSPITAL_PLAN})},
        proposal_class=ProposalClass.BUDGET_FRAME,
    )
