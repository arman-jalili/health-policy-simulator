"""Contract freeze: rebibuildability (issue #305, implements #312)."""

from __future__ import annotations

from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.application.dto import RebuildResult
from consensus_analysis.application.ports import ProjectionRebuilder
from consensus_analysis.application.services import SERVICE_CLASSIFICATION, RebuildProjections
from consensus_analysis.domain.errors import ProjectionRebuildFailed
from consensus_analysis.domain.repositories import ConsensusRepository


def test_a_rebuild_reports_what_it_reproduced() -> None:
    assert field_names(RebuildResult) == ["run_id", "records", "digest"]


def test_the_rebuilder_folds_the_log_into_records() -> None:
    assert parameter_names(ProjectionRebuilder.rebuild) == [
        "self",
        "run_id",
        "stances",
        "vetoes",
        "threshold",
    ]
    assert SERVICE_CLASSIFICATION["ProjectionRebuilder"] == "infrastructure"


def test_the_projection_store_can_be_replaced_from_the_log() -> None:
    assert hasattr(ConsensusRepository, "replace_for_run")
    assert parameter_names(ConsensusRepository.replace_for_run) == ["self", "run_id", "records"]


def test_a_failed_reproducibility_proof_is_an_error_not_a_warning() -> None:
    assert ProjectionRebuildFailed.code == "PROJECTION_REBUILD_FAILED"


def test_the_rebuild_use_case_is_not_implemented_yet() -> None:
    service = RebuildProjections(
        consensus=None,  # type: ignore[arg-type]
        log=None,  # type: ignore[arg-type]
        powers=None,  # type: ignore[arg-type]
        rebuilder=None,  # type: ignore[arg-type]
        uow=None,  # type: ignore[arg-type]
    )
    assert len(service.collaborators()) == 5
    assert parameter_names(RebuildProjections.execute) == ["self", "request"]
    assert SERVICE_CLASSIFICATION["RebuildProjections"] == "application"
