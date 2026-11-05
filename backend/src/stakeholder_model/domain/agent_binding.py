"""AgentBinding aggregate — immutable for the duration of one run (ADR-008).

Canonical: .pi/architecture/modules/stakeholder-model.md
"""

from __future__ import annotations

from dataclasses import dataclass

from evidence_corpus.domain.values import AuthorityTier
from stakeholder_model.domain.values import (
    BindingId,
    PersonaVersion,
    RunId,
    StakeholderId,
)


@dataclass(frozen=True, slots=True)
class AgentBinding:
    """Immutable link of one stakeholder profile to one agent persona in one run."""

    id: BindingId
    run_id: RunId
    stakeholder_id: StakeholderId
    persona_version: PersonaVersion
    allowed_evidence_tiers: frozenset[AuthorityTier]
    red_lines: tuple[str, ...]

    def assert_institution_only(self) -> None:
        """Refuse an incomplete binding; implemented by issue #112."""
        raise NotImplementedError("assert_institution_only is implemented by issue #112")
