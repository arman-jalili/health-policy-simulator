"""ACL isolation: key-store types and imports never leave ``infrastructure``."""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[4] / "src"
IDENTITY_ROOT = SRC_ROOT / "identity_access"
INFRASTRUCTURE_PACKAGE = "identity_access.infrastructure"
KEY_STORE_TYPES = ("ApiKeyRecord", "ApiKeyRepository", "KeyMaterial")
# The composition root is the single place allowed to import adapters; every other module
# (interfaces, application code, other contexts) must stay behind the ACL.
COMPOSITION_ROOT = IDENTITY_ROOT / "composition.py"


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
        if "infrastructure" in relative.parts or path == COMPOSITION_ROOT:
            continue
        source = path.read_text()
        if any(name in source for name in KEY_STORE_TYPES):
            offenders.append(str(relative))

    assert offenders == []


def test_no_module_outside_infrastructure_imports_key_store_infrastructure() -> None:
    offenders = []
    for path in IDENTITY_ROOT.rglob("*.py"):
        relative = path.relative_to(IDENTITY_ROOT)
        if "infrastructure" in relative.parts or path == COMPOSITION_ROOT:
            continue
        for module in _imported_modules(path):
            if module.startswith("identity_access.infrastructure"):
                offenders.append(f"{relative} -> {module}")

    assert offenders == []


def test_no_module_outside_infrastructure_imports_the_key_store_anywhere() -> None:
    """The boundary is repo-wide, not just within the identity_access package."""
    offenders = []
    for path in SRC_ROOT.rglob("*.py"):
        if "identity_access" in path.parts and "infrastructure" in path.parts:
            continue
        if path == COMPOSITION_ROOT:
            continue
        for module in _imported_modules(path):
            if module.startswith(INFRASTRUCTURE_PACKAGE):
                offenders.append(f"{path.relative_to(SRC_ROOT)} -> {module}")

    assert offenders == []


def test_key_store_type_names_stay_inside_infrastructure_repo_wide() -> None:
    offenders = []
    for path in SRC_ROOT.rglob("*.py"):
        if "identity_access" in path.parts and "infrastructure" in path.parts:
            continue
        if path == COMPOSITION_ROOT:
            continue
        source = path.read_text()
        if any(name in source for name in KEY_STORE_TYPES):
            offenders.append(str(path.relative_to(SRC_ROOT)))

    assert offenders == []
