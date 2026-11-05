"""Contract freeze: key-store types never leak outside infrastructure (ACL isolation)."""

from __future__ import annotations

from pathlib import Path

IDENTITY_ROOT = Path(__file__).resolve().parents[4] / "src" / "identity_access"
KEY_STORE_TYPES = ("ApiKeyRecord", "ApiKeyRepository", "KeyMaterial")


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


def test_interfaces_never_import_infrastructure() -> None:
    for path in (IDENTITY_ROOT / "interfaces").rglob("*.py"):
        assert "identity_access.infrastructure" not in path.read_text(), path
