"""Contract freeze: rejected proposals (issue #305, implements #317)."""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.compromise_package import CompromisePackage
from consensus_analysis.domain.entities import PackageComponent, RejectedProposal
from consensus_analysis.domain.events import CompromisePackageComposed
from consensus_analysis.domain.services import ComponentsCompatible
from consensus_analysis.domain.values import (
    ComponentId,
    LogPosition,
    PackageId,
    PackageState,
    RejectedProposalId,
    RunId,
    SupportLevel,
)


def test_the_package_documents_every_rejection() -> None:
    assert field_names(CompromisePackage) == [
        "id",
        "run_id",
        "log_position",
        "components",
        "rejected_proposals",
        "state",
        "events",
    ]
    assert field_names(RejectedProposal) == ["id", "measure", "support", "reason", "holders"]


def test_a_rejection_must_state_why_it_was_not_carried() -> None:
    proposal = RejectedProposal(
        id=RejectedProposalId("rjp_1"),
        measure="raise the fee schedule by 4%",
        support=SupportLevel(value=0.2),
        reason="below the mandate threshold",
    )
    assert proposal.support.value == pytest.approx(0.2)
    with pytest.raises(ValueError, match="reason"):
        RejectedProposal(
            id=RejectedProposalId("rjp_2"),
            measure="raise the fee schedule by 4%",
            support=SupportLevel(value=0.2),
            reason=" ",
        )


def test_composition_takes_the_rejections_as_an_argument() -> None:
    assert parameter_names(CompromisePackage.compose) == ["self", "rejected"]
    assert parameter_names(CompromisePackage.add_component) == ["self", "component"]
    assert parameter_names(CompromisePackage.open) == ["package_id", "run_id", "log_position"]


def test_a_package_without_accepted_components_is_abandoned_not_published() -> None:
    package = CompromisePackage(
        id=PackageId("pkg_1"), run_id=RunId("run_1"), log_position=LogPosition(0)
    )
    assert _state(package) is PackageState.DRAFT
    package.compose(rejected=())
    assert _state(package) is PackageState.ABANDONED
    assert package.component_ids() == ()


def test_compatibility_is_its_own_specification() -> None:
    assert parameter_names(ComponentsCompatible.is_satisfied_by) == ["self", "left", "right"]
    left = PackageComponent(id=ComponentId("cmp_1"), measure="extend the catalogue")
    right = PackageComponent(id=ComponentId("cmp_2"), measure="freeze the fee schedule")
    assert ComponentsCompatible().is_satisfied_by(left=left, right=right) is True
    assert ComponentsCompatible().is_satisfied_by(left=left, right=left) is False


def test_a_declared_conflict_makes_two_components_incompatible() -> None:
    left = PackageComponent(
        id=ComponentId("cmp_1"),
        measure="extend the catalogue",
        conflicts_with=(ComponentId("cmp_2"),),
    )
    right = PackageComponent(id=ComponentId("cmp_2"), measure="freeze the fee schedule")
    specification = ComponentsCompatible()
    assert specification.is_satisfied_by(left=left, right=right) is False
    assert specification.is_satisfied_by(left=right, right=left) is False


def test_the_composition_event_counts_the_rejections() -> None:
    assert CompromisePackageComposed.name == "CompromisePackageComposed"
    assert field_names(CompromisePackageComposed) == [
        "package_id",
        "component_ids",
        "rejected_count",
    ]


# ── issue #317: every proposal without support is documented, none is dropped ──────────────────


def _state(package: CompromisePackage) -> PackageState:
    """Read the state through a function so mypy does not narrow the mutable attribute."""
    return package.state


def _component(key: str, measure: str, **kwargs: object) -> PackageComponent:
    return PackageComponent(
        id=ComponentId(key),
        measure=measure,
        **kwargs,  # type: ignore[arg-type]
    )


def _rejection(key: str, measure: str, support: float = 0.2) -> RejectedProposal:
    return RejectedProposal(
        id=RejectedProposalId(key),
        measure=measure,
        support=SupportLevel(value=support),
        reason="below the mandate threshold",
    )


def test_every_rejection_that_does_not_carry_is_documented() -> None:
    package = CompromisePackage(
        id=PackageId("pkg_1"), run_id=RunId("run_1"), log_position=LogPosition(0)
    )
    package.add_component(_component("cmp_1", "extend the catalogue"))
    rejections = (
        _rejection("rjp_1", "raise the fee schedule by 4%"),
        _rejection("rjp_2", "close two hospital sites"),
    )

    package.compose(rejected=rejections)

    assert _state(package) is PackageState.COMPOSED
    assert package.rejected_proposals == rejections
    assert [proposal.measure for proposal in package.rejected_proposals] == [
        "raise the fee schedule by 4%",
        "close two hospital sites",
    ]


def test_the_composition_event_counts_every_rejection() -> None:
    package = CompromisePackage(
        id=PackageId("pkg_1"), run_id=RunId("run_1"), log_position=LogPosition(0)
    )
    package.add_component(_component("cmp_1", "extend the catalogue"))
    package.compose(rejected=(_rejection("rjp_1", "x"), _rejection("rjp_2", "y")))

    composed = [
        event for event in package.drain_events() if isinstance(event, CompromisePackageComposed)
    ]
    assert len(composed) == 1
    assert composed[0].rejected_count == 2
    assert composed[0].component_ids == (ComponentId("cmp_1"),)


def test_an_incompatible_component_cannot_enter_the_package() -> None:
    from consensus_analysis.domain.errors import IncompatibleComponent

    package = CompromisePackage(
        id=PackageId("pkg_1"), run_id=RunId("run_1"), log_position=LogPosition(0)
    )
    package.add_component(
        _component("cmp_1", "extend the catalogue", conflicts_with=(ComponentId("cmp_2"),))
    )

    with pytest.raises(IncompatibleComponent, match="cmp_2"):
        package.add_component(_component("cmp_2", "freeze the fee schedule"))


def test_a_rejection_must_state_why_it_did_not_carry() -> None:
    from consensus_analysis.domain.errors import IncompleteRejectionList

    package = CompromisePackage(
        id=PackageId("pkg_1"), run_id=RunId("run_1"), log_position=LogPosition(0)
    )
    package.add_component(_component("cmp_1", "extend the catalogue"))
    blank = RejectedProposal(
        id=RejectedProposalId("rjp_1"),
        measure="raise the fee schedule",
        support=SupportLevel(value=0.2),
        reason="below the threshold",
    )
    duplicated = (blank, blank)

    with pytest.raises(IncompleteRejectionList):
        package.compose(rejected=duplicated)


def test_a_package_cannot_be_composed_twice() -> None:
    from consensus_analysis.domain.errors import PackageStateTransition

    package = CompromisePackage(
        id=PackageId("pkg_1"), run_id=RunId("run_1"), log_position=LogPosition(0)
    )
    package.add_component(_component("cmp_1", "extend the catalogue"))
    package.compose(rejected=())

    with pytest.raises(PackageStateTransition):
        package.compose(rejected=())
