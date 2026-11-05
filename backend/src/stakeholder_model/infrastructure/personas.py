"""YAML persona loader adapter (Factory pattern).

Canonical: .pi/architecture/modules/stakeholder-model.md

The concrete loader validates every persona card on load: at least one interest and constraint,
institutional name only, grounded mandate/budget sources and declared persona version. Invalid
configuration aborts boot rather than producing a positionless agent.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from stakeholder_model.domain.stakeholder import Stakeholder, StakeholderProfile
from stakeholder_model.domain.values import (
    BudgetLimit,
    BudgetPeriod,
    Constraint,
    DecisionPriority,
    InstitutionCategory,
    InstitutionIdentity,
    Interest,
    MandateScope,
    MandateSource,
    PersonaVersion,
    PowerSourceKind,
    ProfileVersion,
    ProposalClass,
    StakeholderId,
    VetoRight,
)

_DEFAULT_DIRECTORY = Path(__file__).resolve().parents[3] / "config" / "personas"


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"persona.{field} must be a mapping")
    return value


def _number(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"persona.{field} must be a number") from error


def _integer(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"persona.{field} must be an integer") from error


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"persona.{field} must be non-empty text")
    return value


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as error:
        raise ValueError(f"persona.{field} must be a decimal") from error


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError(f"persona.{field} must be an ISO date") from error


def _source(value: Any, field: str) -> MandateSource:
    payload = _mapping(value, field)
    try:
        kind = PowerSourceKind(_text(payload.get("kind"), f"{field}.kind"))
    except ValueError as error:
        raise ValueError(f"persona.{field}.kind is not a declared source kind") from error
    return MandateSource(
        kind=kind,
        citation=_text(payload.get("citation"), f"{field}.citation"),
        as_of=_date(payload.get("as_of"), f"{field}.as_of"),
    )


def _build(document: dict[str, Any], path: Path) -> Stakeholder:
    code = _text(document.get("code"), "code")
    if path.stem != code:
        raise ValueError(f"persona file {path.name} must be named {code}.yaml")

    identity_payload = _mapping(document.get("identity"), f"{code}.identity")
    try:
        category = InstitutionCategory(_text(identity_payload.get("category"), "identity.category"))
    except ValueError as error:
        raise ValueError(f"persona {code} has an unknown institution category") from error

    identity = InstitutionIdentity(
        name=_text(identity_payload.get("name"), "identity.name"),
        short_name=_text(identity_payload.get("short_name"), "identity.short_name"),
        category=category,
        code=code,
    )

    mandate_payload = _mapping(document.get("mandate_scope"), f"{code}.mandate_scope")
    topics = mandate_payload.get("topics")
    if not isinstance(topics, list) or not all(isinstance(topic, str) for topic in topics):
        raise ValueError(f"persona {code}.mandate_scope.topics must be a list of strings")
    mandate_scope = MandateScope(
        topics=frozenset(topics),
        description=_text(mandate_payload.get("description"), f"{code}.mandate_scope.description"),
        source=_source(mandate_payload.get("source"), f"{code}.mandate_scope.source"),
    )

    budget_payload = _mapping(document.get("budget"), f"{code}.budget")
    try:
        period = BudgetPeriod(_text(budget_payload.get("period"), "budget.period"))
    except ValueError as error:
        raise ValueError(f"persona {code}.budget.period is unknown") from error
    budget = BudgetLimit(
        amount_eur=_decimal(budget_payload.get("amount_eur"), f"{code}.budget.amount_eur"),
        period=period,
        tolerance=_number(budget_payload.get("tolerance", 0.0), f"{code}.budget.tolerance"),
        source=_source(budget_payload.get("source"), f"{code}.budget.source"),
    )

    interests = [
        Interest(
            topic=_text(item.get("topic"), f"{code}.interests.topic"),
            goal=_text(item.get("goal"), f"{code}.interests.goal"),
            weight=_number(item.get("weight"), f"{code}.interests.weight"),
        )
        for item in _list_of_mappings(document.get("interests"), f"{code}.interests")
    ]
    constraints = [
        Constraint(
            statement=_text(item.get("statement"), f"{code}.constraints.statement"),
            topic=_text(item.get("topic"), f"{code}.constraints.topic"),
        )
        for item in _list_of_mappings(document.get("constraints"), f"{code}.constraints")
    ]
    priorities = [
        DecisionPriority(
            rank=_integer(item.get("rank"), f"{code}.priorities.rank"),
            topic=_text(item.get("topic"), f"{code}.priorities.topic"),
        )
        for item in _list_of_mappings(document.get("priorities", []), f"{code}.priorities")
    ]
    red_lines = tuple(_text(item, f"{code}.red_lines") for item in document.get("red_lines", []))
    veto_rights = [
        VetoRight(
            proposal_class=_proposal_class(item.get("proposal_class"), code),
            source=_source(item.get("source"), f"{code}.veto_rights.source"),
        )
        for item in _list_of_mappings(document.get("veto_rights", []), f"{code}.veto_rights")
    ]

    if not interests:
        raise ValueError(f"persona {code} has no interests")
    if not constraints:
        raise ValueError(f"persona {code} has no constraints")

    return Stakeholder(
        id=StakeholderId(f"stk_{code}"),
        identity=identity,
        profile=StakeholderProfile(
            mandate_scope=mandate_scope,
            budget=budget,
            interests=interests,
            constraints=constraints,
            priorities=priorities,
            red_lines=list(red_lines),
            version=ProfileVersion(
                _text(document.get("persona_version"), f"{code}.persona_version")
            ),
        ),
        veto_rights=veto_rights,
    )


def _list_of_mappings(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"persona.{field} must be a list")
    return [_mapping(item, field) for item in value]


def _proposal_class(value: Any, code: str) -> ProposalClass:
    try:
        return ProposalClass(_text(value, f"{code}.veto_rights.proposal_class"))
    except ValueError as error:
        raise ValueError(f"persona {code} has an unknown proposal class") from error


class PersonaFactory:
    """Load persona cards from a YAML directory and validate them before use."""

    def __init__(self, directory: Path | None = None) -> None:
        self._directory = directory or _DEFAULT_DIRECTORY

    def load_all(self) -> list[Stakeholder]:
        """Load and validate all persona cards; duplicate codes are refused."""
        paths = sorted((*self._directory.glob("*.yaml"), *self._directory.glob("*.yml")))
        if not paths:
            raise ValueError(f"no persona cards found in {self._directory}")

        stakeholders: list[Stakeholder] = []
        seen: set[str] = set()
        for path in paths:
            document = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), path.stem)
            stakeholder = _build(document, path)
            code = stakeholder.identity.code
            if code in seen:
                raise ValueError(f"duplicate persona code {code!r}")
            seen.add(code)
            stakeholders.append(stakeholder)
        return stakeholders

    def load(self, code: str) -> Stakeholder:
        """Load one validated persona card by code."""
        for stakeholder in self.load_all():
            if stakeholder.identity.code == code:
                return stakeholder
        raise ValueError(f"persona {code!r} not found in {self._directory}")


__all__ = ["PersonaFactory", "PersonaVersion"]
