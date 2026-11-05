"""ACL isolation: key-store types and imports never leave ``infrastructure``."""

from __future__ import annotations

import ast
from pathlib import Path

IDENTITY_ROOT = Path(__file__).resolve().parents[4] / "src" / "identity_access"
KEY_STORE_TYPES = ("ApiKeyRecord", "ApiKeyRepository", "KeyMaterial")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def test_key_store_types_stay_behind_the_infrastructure_boundary() -> None:
    assert IDENTITY_ROOT.is_dir()
    offenders = []
    for path in IDENTITY_ROOT.rglob("*.py"):
        relative = path.relative_to(IDENTITY_ROOT)
        if "infrastructure" in relative.parts:
            continue
        source = path.read_text()
        if any(name in source for name in KEY_STORE_TYPES):
            offenders.append(str(relative))

    assert offenders == []


def test_no_module_outside_infrastructure_imports_key_store_infrastructure() -> None:
    offenders = []
    for path in IDENTITY_ROOT.rglob("*.py"):
        relative = path.relative_to(IDENTITY_ROOT)
        if "infrastructure" in relative.parts:
            continue
        for module in _imported_modules(path):
            if module.startswith("identity_access.infrastructure"):
                offenders.append(f"{relative} -> {module}")

    assert offenders == []
