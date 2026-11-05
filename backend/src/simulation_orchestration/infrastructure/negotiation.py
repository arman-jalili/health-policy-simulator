"""Temporary no-op ACL until NegotiationSession is implemented (issue #216)."""

from __future__ import annotations

from simulation_orchestration.application.values import (
    NegotiationRunView,
    NegotiationTurnCommand,
    NegotiationTurnView,
    RunId,
    RunPhase,
)


class NoopNegotiationGateway:
    async def load_state(self, run_id: RunId) -> NegotiationRunView:
        return NegotiationRunView(
            run_id=run_id, phase=RunPhase.MANDATE, round=0, next_actor=None, terminal=False
        )

    async def take_turn(self, command: NegotiationTurnCommand) -> NegotiationTurnView:
        return NegotiationTurnView(
            run_id=command.run_id,
            round=command.round,
            actor_id=command.actor_id,
            position_id=None,
            terminal=True,
        )

    async def close_run(self, run_id: RunId) -> None:
        return None
