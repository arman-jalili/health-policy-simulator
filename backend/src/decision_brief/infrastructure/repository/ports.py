"""Implementation boundary re-exports; the repository interface is domain-owned."""

from __future__ import annotations

from decision_brief.domain.repositories import DecisionBriefRepository

__all__ = ["DecisionBriefRepository"]
