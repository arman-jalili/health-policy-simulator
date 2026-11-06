"""Typed JSON snapshot codec for DecisionBrief (issue #407)."""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast

from decision_brief.domain import decision_brief, entities, events, values
from decision_brief.domain.decision_brief import DecisionBrief

_TYPES: dict[str, type[Any]] = {}
for module in (decision_brief, entities, values, events):
    for _, member in inspect.getmembers(module, inspect.isclass):
        if member.__module__ == module.__name__ and (
            dataclasses.is_dataclass(member) or issubclass(member, Enum)
        ):
            _TYPES[member.__name__] = member


def encode(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            "__dataclass__": type(value).__name__,
            "fields": {
                field.name: encode(getattr(value, field.name))
                for field in dataclasses.fields(value)
            },
        }
    if isinstance(value, Enum):
        return {"__enum__": type(value).__name__, "value": value.value}
    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}
    if isinstance(value, (datetime, date)):
        return {"__date__": value.isoformat()}
    if isinstance(value, dict):
        return {"__dict__": [[encode(key), encode(item)] for key, item in value.items()]}
    if isinstance(value, (list, tuple)):
        return [encode(item) for item in value]
    return value


def _hashable(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_hashable(item) for item in value)
    return value


def decode(data: Any) -> Any:
    if isinstance(data, list):
        return [decode(item) for item in data]
    if not isinstance(data, dict):
        return data
    if "__dataclass__" in data:
        cls = _TYPES.get(data["__dataclass__"])
        if cls is None:
            raise ValueError(f"unknown persisted dataclass {data['__dataclass__']!r}")
        return cls(**{key: decode(item) for key, item in data["fields"].items()})
    if "__enum__" in data:
        enum_cls = _TYPES.get(data["__enum__"])
        if enum_cls is None or not issubclass(enum_cls, Enum):
            raise ValueError(f"unknown persisted enum {data['__enum__']!r}")
        return enum_cls(data["value"])
    if "__decimal__" in data:
        return Decimal(data["__decimal__"])
    if "__date__" in data:
        return datetime.fromisoformat(data["__date__"])
    if "__dict__" in data:
        return {_hashable(decode(key)): decode(item) for key, item in data["__dict__"]}
    return data


def encode_brief(brief: DecisionBrief) -> dict[str, Any]:
    return cast(dict[str, Any], encode(brief))


def decode_brief(payload: dict[str, Any]) -> DecisionBrief:
    brief = decode(payload)
    if not isinstance(brief, DecisionBrief):
        raise ValueError("persisted brief snapshot is not a DecisionBrief")
    brief.events = []
    return brief
