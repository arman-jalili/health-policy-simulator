"""Contract freeze: reproduction from the run log (issue #331, implements #346).

The brief is a projection: the log position and snapshot are part of the frozen input contract.
"""

from __future__ import annotations

from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.domain.errors import BriefReproductionMismatch
from decision_brief.domain.projections import (
    ConsensusProjection,
    ReproductionInput,
    RunProjection,
)
from decision_brief.domain.services import ReproductionChecker


def test_run_projection_carries_the_reproduction_anchor() -> None:
    fields = field_names(RunProjection)
    assert "log_position" in fields
    assert "snapshot_ref" in fields
    assert fields[:2] == ["run_id", "question"]


def test_consensus_projection_carries_its_log_position() -> None:
    assert "log_position" in field_names(ConsensusProjection)


def test_reproduction_input_is_the_complete_allowed_read_set() -> None:
    assert field_names(ReproductionInput) == ["run", "consensus"]


def test_the_reproduction_checker_is_a_domain_contract() -> None:
    assert parameter_names(ReproductionChecker.assert_reproduces) == [
        "self",
        "published",
        "regenerated",
    ]


def test_reproduction_mismatch_names_run_and_section() -> None:
    error = BriefReproductionMismatch("run_01J", "impact")
    assert error.code == "BRIEF_REPRODUCTION_MISMATCH"
    assert error.run_id == "run_01J"
    assert error.section == "impact"
