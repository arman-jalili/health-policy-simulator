"""Helpers shared by the EvidenceRetrieval contract-freeze tests.

The contract tests inspect structure (fields, members, layers, signatures) rather than behaviour:
behaviour belongs to the implementation issues that follow.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parents[2] / "src" / "evidence_retrieval"


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


def public_fields(module_path: Path, class_name: str) -> set[str]:
    """Return the annotated fields of a dataclass without importing the module."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
                for target in [statement.target]
            }
    raise AssertionError(f"{class_name} not found in {module_path}")


def imported_names(module_path: Path) -> set[str]:
    """Return every dotted import target in a Python module."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names
