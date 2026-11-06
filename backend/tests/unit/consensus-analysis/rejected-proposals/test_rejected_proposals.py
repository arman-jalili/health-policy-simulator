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


def test_composition_is_not_implemented_yet() -> None:
    package = CompromisePackage(
        id=PackageId("pkg_1"), run_id=RunId("run_1"), log_position=LogPosition(0)
    )
    assert package.state is PackageState.DRAFT
    assert package.component_ids() == ()
    with pytest.raises(NotImplementedError, match="#317"):
        package.compose(rejected=())


def test_compatibility_is_its_own_specification() -> None:
    assert parameter_names(ComponentsCompatible.is_satisfied_by) == ["self", "left", "right"]
    left = PackageComponent(id=ComponentId("cmp_1"), measure="extend the catalogue")
    right = PackageComponent(id=ComponentId("cmp_2"), measure="freeze the fee schedule")
    with pytest.raises(NotImplementedError, match="#317"):
        ComponentsCompatible().is_satisfied_by(left=left, right=right)


def test_the_composition_event_counts_the_rejections() -> None:
    assert CompromisePackageComposed.name == "CompromisePackageComposed"
    assert field_names(CompromisePackageComposed) == [
        "package_id",
        "component_ids",
        "rejected_count",
    ]
