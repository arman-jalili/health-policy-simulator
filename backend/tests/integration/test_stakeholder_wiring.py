"""Integration proof: StakeholderModel is mounted and reachable through the public API."""

from __future__ import annotations

import httpx

from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence
from tests.conftest import TEST_DATABASE_URL


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        persistence=Persistence.MEMORY,
        auth_mode=AuthMode.DEMO,
    )


async def test_registry_selection_and_binding_run_through_the_public_api() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        registry = await client.get("/api/v1/stakeholders")
        assert registry.status_code == 200, registry.text
        assert len(registry.json()["items"]) == 9

        selected = await client.post(
            "/api/v1/runs/run_1/stakeholders:select",
            json={"mandate": "Wie reduzieren wir die Wartezeiten auf Kassenstellen?"},
        )
        assert selected.status_code == 200, selected.text
        items = selected.json()["items"]
        assert len(items) >= 7
        assert all(0.0 <= item["materiality"] <= 1.0 for item in items)

        stakeholder_ids = [item["stakeholder_id"] for item in items[:2]]
        bound = await client.post(
            "/api/v1/runs/run_1/stakeholders:bind",
            json={"stakeholder_ids": stakeholder_ids},
        )
        assert bound.status_code == 200, bound.text
        assert len(bound.json()["bindings"]) == 2

        history = await client.get(
            f"/api/v1/stakeholders/{stakeholder_ids[0]}/history",
            params={"usable_only": "false"},
        )
        assert history.status_code == 200, history.text
        assert history.json()["positions"] == []


async def test_container_publishes_the_allowlist_to_the_guard() -> None:
    app = create_app(_settings())
    container = app.state.stakeholder_model

    published = await container.publish_allowlist.execute()

    assert len(published.institutions) == 9
    assert container.guard.codes == {item.code for item in published.institutions}
    assert all(container.guard.recognises(item.code) for item in published.institutions)
