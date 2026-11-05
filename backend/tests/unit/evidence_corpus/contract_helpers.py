"""Helpers shared by the evidence-corpus contract tests.

The contract freeze tests inspect structure (fields, members, signatures) rather than behaviour:
behaviour belongs to the implementation issues that follow.
"""

from __future__ import annotations

import dataclasses
import inspect
from typing import Any


def field_names(cls: type) -> list[str]:
    """Declared dataclass fields, in declaration order."""
    return [f.name for f in dataclasses.fields(cls)]


def field_types(cls: type) -> dict[str, str]:
    """Declared field annotations as strings (postponed evaluation safe)."""
    return {name: str(annotation) for name, annotation in cls.__annotations__.items()}


def method_names(protocol: type) -> set[str]:
    """Public members declared in a Protocol/class body."""
    return {
        name
        for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def parameter_names(func: Any) -> list[str]:
    return list(inspect.signature(func).parameters)


def enum_values(enum_cls: type) -> set[str]:
    return {str(member.value) for member in enum_cls}  # type: ignore[attr-defined]
