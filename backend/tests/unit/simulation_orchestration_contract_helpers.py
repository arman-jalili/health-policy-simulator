"""Helpers for SimulationOrchestration contract-freeze tests (structure, not behaviour)."""

from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parents[2] / "src" / "simulation_orchestration"


def field_names(cls: type) -> list[str]:
    return [field.name for field in dataclasses.fields(cls)]


def annotation_names(cls: type) -> list[str]:
    return list(getattr(cls, "__annotations__", {}))


def method_names(cls: type) -> set[str]:
    return {
        name for name, value in vars(cls).items() if not name.startswith("_") and callable(value)
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


def application_python_files() -> list[Path]:
    return sorted((SRC / "application").glob("*.py"))
