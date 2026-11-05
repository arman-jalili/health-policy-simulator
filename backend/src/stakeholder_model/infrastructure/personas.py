"""YAML persona loader adapter (Factory pattern).

Canonical: .pi/architecture/modules/stakeholder-model.md

The concrete loader validates every persona card on load: at least one interest and constraint,
institutional name only, and grounded mandate sources. Invalid configuration aborts boot.
"""

from __future__ import annotations

from pathlib import Path

from stakeholder_model.domain.stakeholder import Stakeholder


class PersonaFactory:
    """Load persona cards from a YAML directory; implemented by issue #114."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def load_all(self) -> list[Stakeholder]:
        """Load and validate all persona cards; implemented by issue #114."""
        raise NotImplementedError("PersonaFactory.load_all is implemented by issue #114")

    def load(self, code: str) -> Stakeholder:
        """Load one validated persona card; implemented by issue #114."""
        raise NotImplementedError("PersonaFactory.load is implemented by issue #114")
