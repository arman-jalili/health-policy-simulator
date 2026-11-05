"""Contract freeze: a veto is class-scoped and cannot name one proposal (invariant 7)."""

from __future__ import annotations

from datetime import date

import pytest
from tests.unit.stakeholder_contract_helpers import field_names

from shared.errors import AppError
from stakeholder_model.domain.errors import VetoNarrowedToProposal
from stakeholder_model.domain.values import (
    MandateSource,
    PowerSourceKind,
    ProposalClass,
    VetoRight,
)


def _source() -> MandateSource:
    return MandateSource(
        kind=PowerSourceKind.STATUTORY,
        citation="§ 23 ASVG",
        as_of=date(2026, 1, 1),
    )


def test_veto_right_has_only_a_proposal_class() -> None:
    assert field_names(VetoRight) == ["proposal_class", "source"]
    assert "proposal_id" not in field_names(VetoRight)


def test_a_proposal_id_is_not_even_representable() -> None:
    with pytest.raises(TypeError):
        VetoRight(  # type: ignore[call-arg]
            proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE,
            source=_source(),
            proposal_id="prop_1",
        )


def test_statutory_benefit_change_is_a_declared_class() -> None:
    right = VetoRight(
        proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE,
        source=_source(),
    )

    assert right.proposal_class is ProposalClass.STATUTORY_BENEFIT_CHANGE


def test_narrowing_error_is_frozen() -> None:
    assert issubclass(VetoNarrowedToProposal, AppError)
    assert VetoNarrowedToProposal.code == "VETO_NARROWED_TO_PROPOSAL"
