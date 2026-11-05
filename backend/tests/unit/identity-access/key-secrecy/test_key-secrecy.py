"""Key secrecy: hashed at rest, plaintext returned exactly once (ADR-005)."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from identity_access.infrastructure.key_resolver import KeyResolver
from identity_access.infrastructure.key_store import HashedApiKeyStore
from identity_access.infrastructure.keys import Sha256ApiKeyFactory, hash_key
from identity_access.infrastructure.ports import ApiKeyFactory, KeyMaterial
from identity_access.infrastructure.repository.records import ApiKeyRecord
from identity_access.interfaces.dto import CreateApiKeyCommand, IssuedApiKey
from identity_access.interfaces.errors import ApiKeyNotFoundError, AuthenticationRequiredError
from identity_access.interfaces.ports import ApiKeyAdminPort
from identity_access.interfaces.types import Role, Scope

MOMENT = datetime(2026, 11, 5, 9, 30, tzinfo=UTC)


class FakeApiKeyRepository:
    """In-memory stand-in for the SQLAlchemy port; exercises the store without a database."""

    def __init__(self) -> None:
        self.records: dict[str, ApiKeyRecord] = {}

    async def add(self, record: ApiKeyRecord) -> None:
        self.records[record.key_id] = record

    async def get(self, key_id: str) -> ApiKeyRecord | None:
        return self.records.get(key_id)

    async def find_by_hash(self, key_hash: str) -> ApiKeyRecord | None:
        return next(
            (record for record in self.records.values() if record.key_hash == key_hash),
            None,
        )

    async def list(self) -> list[ApiKeyRecord]:
        return list(self.records.values())

    async def revoke(self, key_id: str, revoked_at: datetime) -> None:
        record = self.records.get(key_id)
        if record is not None:
            self.records[key_id] = replace(record, revoked_at=revoked_at)


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


def test_factory_derives_a_prefixed_salted_hash() -> None:
    material = Sha256ApiKeyFactory().generate()
    key_id, separator, secret = material.plaintext_key.partition(".")

    assert separator == "."
    assert key_id == material.key_id
    assert material.key_hash == hash_key(secret, material.salt)
    assert len(material.key_hash) == hashlib.sha256().digest_size * 2
    assert secret not in material.key_hash


async def test_store_returns_plaintext_once_and_persists_only_the_hash() -> None:
    repository = FakeApiKeyRepository()
    store = HashedApiKeyStore(repository, Sha256ApiKeyFactory())

    issued = await store.create_key(CreateApiKeyCommand(label="ops", role=Role.OPERATOR))

    stored = repository.records[issued.key_id]
    assert issued.key.startswith(f"{issued.key_id}.")
    assert stored.key_hash != issued.key
    assert issued.key.split(".", 1)[1] not in stored.key_hash
    summaries = await store.list_keys()
    assert [summary.key_id for summary in summaries] == [issued.key_id]
    assert "key" not in summaries[0].__dataclass_fields__


async def test_lookup_succeeds_until_revocation() -> None:
    repository = FakeApiKeyRepository()
    store = HashedApiKeyStore(repository, Sha256ApiKeyFactory())
    issued = await store.create_key(CreateApiKeyCommand(label="ops", role=Role.OPERATOR))

    record = await store.lookup(issued.key)
    assert record is not None
    assert record.is_active is True

    await store.revoke_key(issued.key_id)
    assert await store.lookup(issued.key) is None

    with pytest.raises(ApiKeyNotFoundError):
        await store.revoke_key("key_missing")


async def test_resolver_maps_a_key_to_its_operator_principal() -> None:
    repository = FakeApiKeyRepository()
    store = HashedApiKeyStore(repository, Sha256ApiKeyFactory())
    issued = await store.create_key(CreateApiKeyCommand(label="ops", role=Role.OPERATOR))
    resolver = KeyResolver(store)

    principal = await resolver.resolve(issued.key)

    assert principal.label == "ops"
    assert principal.role is Role.OPERATOR
    assert principal.has_scope(Scope.CORPUS_WRITE)
    assert principal.is_demo is False

    with pytest.raises(AuthenticationRequiredError):
        await resolver.resolve("not-a-key")

    with pytest.raises(AuthenticationRequiredError):
        await resolver.resolve(None)
