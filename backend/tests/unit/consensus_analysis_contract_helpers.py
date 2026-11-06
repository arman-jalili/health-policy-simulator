"""Helpers for ConsensusAnalysis contract-freeze tests (structure, not behaviour).

The freeze tests assert the shape of the frozen contracts: dataclass fields, method names, parameter
names, enum values, route tables and import hygiene. Behaviour is proved by the implementation
issues that follow, so nothing here asserts that a rule works — only that its contract exists and
cannot drift silently.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parents[2] / "src" / "consensus_analysis"


def field_names(cls: type) -> list[str]:
    return [field.name for field in dataclasses.fields(cls)]


def annotation_names(cls: type) -> list[str]:
    return list(getattr(cls, "__annotations__", {}))


def method_names(cls: type) -> set[str]:
    return {
        name
        for name, value in vars(cls).items()
        if not name.startswith("_")
        and (callable(value) or isinstance(value, (classmethod, staticmethod)))
    }


def parameter_names(func: Any) -> list[str]:
    return list(inspect.signature(func).parameters)


def enum_values(enum_cls: type) -> set[str]:
    return {str(member.value) for member in enum_cls}  # type: ignore[attr-defined]


def source(relative: str) -> str:
    return (SRC / relative).read_text(encoding="utf-8")


def imported_modules(relative: str) -> set[str]:
    tree = ast.parse(source(relative))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def domain_python_files() -> list[Path]:
    return sorted(path for path in (SRC / "domain").glob("*.py") if path.name != "__init__.py")
