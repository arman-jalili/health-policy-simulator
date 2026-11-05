"""Contract freeze: plaintext keys are returned once and never rendered in logs."""

from __future__ import annotations

from datetime import UTC, datetime

from identity_access.infrastructure.ports import ApiKeyFactory, KeyMaterial
from identity_access.interfaces.dto import IssuedApiKey
from identity_access.interfaces.ports import ApiKeyAdminPort
from identity_access.interfaces.types import Role

MOMENT = datetime(2026, 11, 5, 9, 30, tzinfo=UTC)


def test_issued_key_hides_the_plaintext_from_repr() -> None:
    issued = IssuedApiKey(
        key_id="key_1",
        key="hps_plaintext_once",
        label="ops",
        role=Role.OPERATOR,
        created_at=MOMENT,
    )

    assert issued.key == "hps_plaintext_once"
    assert "hps_plaintext_once" not in repr(issued)


def test_admin_port_freezes_the_key_lifecycle() -> None:
    for name in ("create_key", "list_keys", "revoke_key"):
        assert hasattr(ApiKeyAdminPort, name)


def test_key_material_hides_secrets_and_hashes() -> None:
    material = KeyMaterial(
        key_id="key_1",
        plaintext_key="hps_plaintext_once",
        key_hash="sha256:deadbeef",
        salt="salt",
    )

    assert "hps_plaintext_once" not in repr(material)
    assert "sha256:deadbeef" not in repr(material)
    assert hasattr(ApiKeyFactory, "generate")
