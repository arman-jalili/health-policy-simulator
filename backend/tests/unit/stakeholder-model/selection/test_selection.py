"""Contract freeze: materiality selection and its bounded score."""

from __future__ import annotations

import inspect

import pytest
from tests.unit.stakeholder_contract_helpers import field_names, method_names

from stakeholder_model.application import services
from stakeholder_model.application.dto import SelectionResult, SelectStakeholdersResult
from stakeholder_model.domain.services import MaterialityScorer
from stakeholder_model.domain.values import MaterialityScore, StakeholderId


def test_materiality_score_is_bounded() -> None:
    assert MaterialityScore(0.0).value == 0.0
    assert MaterialityScore(1.0).value == 1.0
    with pytest.raises(ValueError, match="within"):
        MaterialityScore(1.01)


def test_selection_result_carries_id_and_materiality() -> None:
    assert field_names(SelectionResult) == ["stakeholder_id", "materiality"]
    assert field_names(SelectStakeholdersResult) == [
        "run_id",
        "mandate",
        "selections",
        "priorities",
    ]
    result = SelectionResult(
        stakeholder_id=StakeholderId("stk_1"),
        materiality=MaterialityScore(0.8),
    )
    assert result.materiality.value == 0.8


def test_selection_service_and_policy_are_frozen() -> None:
    assert inspect.iscoroutinefunction(services.SelectRelevantStakeholders.execute)
    assert method_names(MaterialityScorer) == {"score"}
    assert not inspect.iscoroutinefunction(MaterialityScorer.score)
