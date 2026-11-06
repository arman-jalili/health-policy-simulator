"""``ConsensusRecord`` aggregate: veto precedence, threshold and history assertion (issue #306).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Invariants 2, 3, 11)

AC 1 — 7/9 support for a vetoed proposal class yields `VetoBlockedOutcome`, never consensus.
AC 2 — support below the threshold returns partial + minority, not consensus.
AC 3 — a stance not present in the run log raises `StanceNotInHistory`.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.errors import StanceNotInHistory
from consensus_analysis.domain.events import (
    ConsensusBlockedByVeto,
    ConsensusDetermined,
    MinorityPositionRecorded,
)
from consensus_analysis.domain.values import (
    ConsensusId,
    ConsensusOutcomeKind,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    StakeholderId,
    Stance,
    StanceSnapshot,
    SupportLevel,
    TopicRef,
)

TOPIC = TopicRef("waiting_times")
PROPOSAL_CLASS = ProposalClass.SERVICE_CATALOGUE


def _snapshot(
    key: str,
    stance: Stance,
    *,
    position: int,
    weight: float = 1.0,
    recorded: bool = True,
) -> tuple[StakeholderId, StanceSnapshot]:
    stakeholder = StakeholderId(key)
    return stakeholder, StanceSnapshot(
        stakeholder=stakeholder,
        stance=stance,
        topic=TOPIC,
        weight=weight,
        recorded=recorded,
        log_position=LogPosition(position),
    )


def _stances(*items: tuple[StakeholderId, StanceSnapshot]) -> dict[StakeholderId, StanceSnapshot]:
    return dict(items)


def _record(
    stances: Mapping[StakeholderId, StanceSnapshot],
    *,
    vetoes: Mapping[StakeholderId, frozenset[ProposalClass]] | None = None,
    threshold: float = 0.6,
) -> ConsensusRecord:
    return ConsensusRecord.open(
        consensus_id=ConsensusId("cns_1"),
        run_id=RunId("run_1"),
        topic=TOPIC,
        proposal_class=PROPOSAL_CLASS,
        threshold=ConsensusThreshold.from_mandate(threshold),
        stances=stances,
        vetoes=vetoes or {},
        log_position=LogPosition(42),
    )


# ── AC 1: veto precedence ────────────────────────────────────────────────────────────────────


def test_seven_of_nine_support_for_a_vetoed_class_is_blocked_never_consensus() -> None:
    stances = _stances(
        *(_snapshot(f"stk_s{i}", Stance.SUPPORT, position=i) for i in range(7)),
        _snapshot("stk_bva", Stance.OPPOSE, position=7),
        _snapshot("stk_opp", Stance.OPPOSE, position=8),
    )
    record = _record(stances, vetoes={StakeholderId("stk_bva"): frozenset({PROPOSAL_CLASS})})

    outcome = record.determine()

    assert outcome.kind is ConsensusOutcomeKind.VETO_BLOCKED
    assert outcome.veto is not None
    assert outcome.veto.holders == (StakeholderId("stk_bva"),)
    assert outcome.support.value == pytest.approx(7 / 9)


def test_a_blocked_class_emits_the_audit_event_and_never_a_consensus_event() -> None:
    stances = _stances(
        *(_snapshot(f"stk_s{i}", Stance.SUPPORT, position=i) for i in range(7)),
        _snapshot("stk_bva", Stance.OPPOSE, position=7),
        _snapshot("stk_opp", Stance.OPPOSE, position=8),
    )
    record = _record(stances, vetoes={StakeholderId("stk_bva"): frozenset({PROPOSAL_CLASS})})
    record.determine()

    events = record.drain_events()

    blocked = [event for event in events if isinstance(event, ConsensusBlockedByVeto)]
    assert len(blocked) == 1
    assert blocked[0].holder_ids == (StakeholderId("stk_bva"),)
    assert blocked[0].proposal_class is PROPOSAL_CLASS
    assert not [event for event in events if isinstance(event, ConsensusDetermined)]


def test_a_veto_over_another_class_does_not_block() -> None:
    stances = _stances(
        *(_snapshot(f"stk_s{i}", Stance.SUPPORT, position=i) for i in range(7)),
        _snapshot("stk_bva", Stance.OPPOSE, position=7),
        _snapshot("stk_opp", Stance.OPPOSE, position=8),
    )
    record = _record(
        stances,
        vetoes={StakeholderId("stk_bva"): frozenset({ProposalClass.BUDGET_FRAME})},
    )

    assert record.determine().kind is ConsensusOutcomeKind.CONSENSUS


# ── AC 2: threshold ──────────────────────────────────────────────────────────────────────────


def test_support_below_the_threshold_is_partial_plus_minority_never_consensus() -> None:
    stances = _stances(
        _snapshot("stk_1", Stance.SUPPORT, position=0),
        _snapshot("stk_2", Stance.SUPPORT, position=1),
        _snapshot("stk_3", Stance.OPPOSE, position=2),
        _snapshot("stk_4", Stance.OPPOSE, position=3),
        _snapshot("stk_5", Stance.QUALIFY, position=4),
    )
    record = _record(stances, threshold=0.6)

    outcome = record.determine()

    assert outcome.kind is ConsensusOutcomeKind.PARTIAL
    assert outcome.support.value == pytest.approx(2 / 5)
    assert record.minority_holders() == (
        StakeholderId("stk_3"),
        StakeholderId("stk_4"),
        StakeholderId("stk_5"),
    )
    assert record.drain_events(), "a partial outcome must still be recorded"


def test_support_exactly_at_the_threshold_is_consensus() -> None:
    stances = _stances(
        *(_snapshot(f"stk_s{i}", Stance.SUPPORT, position=i) for i in range(3)),
        *(_snapshot(f"stk_o{i}", Stance.OPPOSE, position=10 + i) for i in range(2)),
    )
    record = _record(stances, threshold=0.6)

    outcome = record.determine()

    assert outcome.kind is ConsensusOutcomeKind.CONSENSUS
    assert outcome.support.value == pytest.approx(0.6)


def test_nobody_expressing_a_position_is_unresolved_not_consensus() -> None:
    stances = _stances(*(_snapshot(f"stk_a{i}", Stance.ABSTAIN, position=i) for i in range(3)))
    record = _record(stances, threshold=0.6)

    assert record.determine().kind is ConsensusOutcomeKind.UNRESOLVED


# ── AC 3: history assertion ─────────────────────────────────────────────────────────────────


def test_a_stance_absent_from_the_run_log_raises() -> None:
    stances = _stances(
        _snapshot("stk_1", Stance.SUPPORT, position=0),
        _snapshot("stk_ghost", Stance.SUPPORT, position=1, recorded=False),
    )
    record = _record(stances, threshold=0.6)

    with pytest.raises(StanceNotInHistory) as raised:
        record.determine()

    assert raised.value.code == "STANCE_NOT_IN_HISTORY"
    assert raised.value.missing == ("stk_ghost",)


def test_the_assertion_fires_before_any_outcome_is_concluded() -> None:
    stances = _stances(_snapshot("stk_ghost", Stance.SUPPORT, position=0, recorded=False))
    record = _record(stances, threshold=0.6)

    with pytest.raises(StanceNotInHistory):
        record.determine()

    assert record.outcome is None
    assert record.events == []


def test_an_unrecorded_stance_adds_no_support_weight() -> None:
    stances = _stances(
        *(_snapshot(f"stk_s{i}", Stance.SUPPORT, position=i) for i in range(3)),
        _snapshot("stk_ghost", Stance.OPPOSE, position=5, recorded=False),
    )
    assert SupportLevel.weighted(stances).value == pytest.approx(1.0)


# ── Reproducibility (roadmap W9) ─────────────────────────────────────────────────────────────


def test_derivation_is_independent_of_insertion_order() -> None:
    items = [
        _snapshot("stk_1", Stance.SUPPORT, position=0),
        _snapshot("stk_2", Stance.OPPOSE, position=1),
        _snapshot("stk_3", Stance.SUPPORT, position=2),
    ]
    forward = _record(_stances(*items), threshold=0.6)
    backward = _record(_stances(*reversed(items)), threshold=0.6)

    assert forward.determine() == backward.determine()
    assert forward.supporting_stakeholders() == backward.supporting_stakeholders()
    assert forward.drain_events() == backward.drain_events()


# ── Structure (frozen by issue #305) ────────────────────────────────────────────────────────


def test_aggregate_fields_are_frozen() -> None:
    assert field_names(ConsensusRecord) == [
        "id",
        "run_id",
        "topic",
        "proposal_class",
        "threshold",
        "stances",
        "vetoes",
        "log_position",
        "outcome",
        "majority",
        "minorities",
        "unresolved",
        "events",
    ]


def test_open_signature_is_frozen() -> None:
    assert parameter_names(ConsensusRecord.open) == [
        "consensus_id",
        "run_id",
        "topic",
        "proposal_class",
        "threshold",
        "stances",
        "vetoes",
        "log_position",
    ]


def test_a_freshly_opened_record_concludes_nothing() -> None:
    record = _record(_stances(_snapshot("stk_1", Stance.SUPPORT, position=0)))
    assert record.outcome is None
    assert record.majority is None
    assert record.minorities == ()
    assert record.drain_events() == ()


def test_a_minority_position_must_name_a_holder() -> None:
    from consensus_analysis.domain.entities import MinorityPosition

    record = _record(_stances(_snapshot("stk_1", Stance.SUPPORT, position=0)))
    with pytest.raises(ValueError, match="holder"):
        record.record_minority(MinorityPosition(holders=(), objections=()))


def test_minority_events_are_emitted_once_per_stakeholder() -> None:
    stances = _stances(
        _snapshot("stk_o1", Stance.OPPOSE, position=0),
        _snapshot("stk_o2", Stance.QUALIFY, position=1),
    )
    record = _record(stances, threshold=0.9)
    record.determine()

    recorded = [e for e in record.drain_events() if isinstance(e, MinorityPositionRecorded)]
    assert [event.holders for event in recorded] == [
        (StakeholderId("stk_o1"),),
        (StakeholderId("stk_o2"),),
    ]
