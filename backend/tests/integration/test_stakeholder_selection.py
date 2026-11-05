"""Integration proof: materiality selection over the real nine persona cards."""

from __future__ import annotations

from pathlib import Path

from stakeholder_model.application.commands import SelectRelevantStakeholdersRequest
from stakeholder_model.application.services import SelectRelevantStakeholders
from stakeholder_model.domain.repositories import StakeholderRepository
from stakeholder_model.domain.services import WeightedInterestScorer
from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import RunId, StakeholderId
from stakeholder_model.infrastructure.personas import PersonaFactory

PERSONA_DIRECTORY = Path("config/personas")


class InMemoryStakeholderRepository:
    """Test adapter exposing the real loaded persona registry."""

    def __init__(self, stakeholders: list[Stakeholder]) -> None:
        self._stakeholders = {stakeholder.id: stakeholder for stakeholder in stakeholders}

    async def get(self, stakeholder_id: StakeholderId) -> Stakeholder | None:
        return self._stakeholders.get(stakeholder_id)

    async def save(self, stakeholder: Stakeholder) -> None:
        self._stakeholders[stakeholder.id] = stakeholder

    async def all_registered(self) -> list[Stakeholder]:
        return list(self._stakeholders.values())


async def test_waiting_time_question_selects_at_least_seven_of_nine() -> None:
    repository: StakeholderRepository = InMemoryStakeholderRepository(
        PersonaFactory(PERSONA_DIRECTORY).load_all()
    )
    service = SelectRelevantStakeholders(
        repository=repository,
        scorer=WeightedInterestScorer(),
    )

    result = await service.execute(
        SelectRelevantStakeholdersRequest(
            run_id=RunId("run_1"),
            mandate="Wie reduzieren wir die Wartezeiten auf Kassenstellen?",
        )
    )

    assert len(result.selections) >= 7
    assert all(0.0 <= selection.materiality.value <= 1.0 for selection in result.selections)
    selected = {selection.stakeholder_id for selection in result.selections}
    assert StakeholderId("stk_oegk") in selected
    assert StakeholderId("stk_patientenanwaltschaft") in selected
    assert StakeholderId("stk_apothekerkammer") not in selected
    assert StakeholderId("stk_sozialversicherung") not in selected


async def test_unrelated_mandate_selects_nobody() -> None:
    repository: StakeholderRepository = InMemoryStakeholderRepository(
        PersonaFactory(PERSONA_DIRECTORY).load_all()
    )
    service = SelectRelevantStakeholders(
        repository=repository,
        scorer=WeightedInterestScorer(),
    )

    result = await service.execute(
        SelectRelevantStakeholdersRequest(
            run_id=RunId("run_1"),
            mandate="Weltraumtourismus und Tiefseeforschung",
        )
    )

    assert result.selections == ()
