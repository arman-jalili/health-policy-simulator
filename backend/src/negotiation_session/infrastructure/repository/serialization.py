"""JSON snapshot codec for the NegotiationSession aggregate (issue #405).

The domain owns its shape (ADR-002), so persistence stores a typed JSON snapshot rather than
duplicating every entity column. The codec is intentionally generic: dataclasses are tagged with
their class name, enums with their value and decimals/dates with an explicit tag. Loading rebuilds
the same dataclass graph the aggregate had before the process restarted.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast

from negotiation_session.domain import entities, events, values
from negotiation_session.domain.simulation_run import SimulationRun

_TYPES: dict[str, type[Any]] = {"SimulationRun": SimulationRun}
for module in (entities, values, events):
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
        class_name = data["__dataclass__"]
        cls = _TYPES.get(class_name)
        if cls is None:
            raise ValueError(f"unknown persisted dataclass {class_name!r}")
        fields = {key: decode(item) for key, item in data["fields"].items()}
        return cls(**fields)
    if "__enum__" in data:
        class_name = data["__enum__"]
        enum_cls = _TYPES.get(class_name)
        if enum_cls is None or not issubclass(enum_cls, Enum):
            raise ValueError(f"unknown persisted enum {class_name!r}")
        return enum_cls(data["value"])
    if "__decimal__" in data:
        return Decimal(data["__decimal__"])
    if "__date__" in data:
        return datetime.fromisoformat(data["__date__"])
    if "__dict__" in data:
        return {_hashable(decode(key)): decode(item) for key, item in data["__dict__"]}
    return data


def encode_run(run: SimulationRun) -> dict[str, Any]:
    return cast(dict[str, Any], encode(run))


def decode_run(payload: dict[str, Any]) -> SimulationRun:
    run = decode(payload)
    if not isinstance(run, SimulationRun):
        raise ValueError("persisted negotiation snapshot is not a SimulationRun")
    run.events = []
    return run
