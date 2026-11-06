"""Provenance facts from the NegotiationSession aggregate (issue #407)."""

from __future__ import annotations

from governance_compliance.application.dto import ProvenanceFacts
from governance_compliance.application.values import PositionId
from negotiation_session.application.services import GetSimulationRun
from negotiation_session.domain.values import RunId


class NegotiationProvenanceFacts:
    """Resolve a position to its evidence, arguments, invocation and model reference."""

    def __init__(self, *, runs: GetSimulationRun, model: str, prompt_version: str) -> None:
        self._runs = runs
        self._model = model
        self._prompt_version = prompt_version

    async def load(self, position_id: PositionId) -> ProvenanceFacts | None:
        for candidate in await self._runs.all_ids():
            run = await self._runs.load(RunId(str(candidate)))
            for round_ in run.rounds:
                for position in round_.positions.values():
                    if str(position.id) != str(position_id):
                        continue
                    arguments = [
                        argument
                        for round_item in run.rounds
                        for argument in round_item.arguments
                        if argument.stakeholder == position.stakeholder
                    ]
                    invocation = next(
                        (
                            argument.invocation_id
                            for argument in arguments
                            if argument.invocation_id is not None
                        ),
                        None,
                    )
                    return ProvenanceFacts(
                        position_id=position_id,
                        evidence_ids=tuple(str(item.evidence_id) for item in position.evidence),
                        argument_ids=tuple(str(argument.id) for argument in arguments),
                        invocation_id=str(invocation) if invocation is not None else None,
                        prompt_version=self._prompt_version,
                        model=self._model,
                    )
        return None
