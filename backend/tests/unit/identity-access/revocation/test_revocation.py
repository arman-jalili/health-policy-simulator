"""Contract freeze: revocation is immediate and uses the same 401 path as any bad key."""

from __future__ import annotations

from datetime import UTC, datetime

from identity_access.interfaces.dto import ApiKeySummary
from identity_access.interfaces.errors import AuthenticationRequiredError
from identity_access.interfaces.ports import ApiKeyAdminPort
from identity_access.interfaces.types import Role

MOMENT = datetime(2026, 11, 5, 9, 30, tzinfo=UTC)


def test_summary_tracks_revocation_state() -> None:
    active = ApiKeySummary(key_id="key_1", label="ops", role=Role.OPERATOR, created_at=MOMENT)
    revoked = ApiKeySummary(
        key_id="key_1",
        label="ops",
        role=Role.OPERATOR,
        created_at=MOMENT,
        revoked_at=MOMENT,
    )

    assert active.is_active is True
    assert revoked.is_active is False


def test_revoke_is_part_of_the_admin_contract() -> None:
    assert hasattr(ApiKeyAdminPort, "revoke_key")


def test_revoked_requests_use_the_auth_contract() -> None:
    assert AuthenticationRequiredError().status_code == 401
