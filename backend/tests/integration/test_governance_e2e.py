"""E2E: the governance guard is reachable through the public API (issue #260)."""

from __future__ import annotations

import httpx

from shared.app import create_app
from shared.config import Settings
from shared.enums import Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


async def test_guard_rewrites_a_person_through_the_public_api() -> None:
    app = create_app(
        Settings(_env_file=None, database_url=DATABASE_URL, persistence=Persistence.MEMORY)
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/governance/check",
            json={
                "text": "Dr. Müller sagte, die Reform sei notwendig.",
                "speaker_kind": "institution",
                "invocation_id": "inv_e2e_1",
                "run_id": "run_e2e_1",
            },
        )
    await app.state.db.dispose()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"] == "rewrite"
    assert "Dr. Müller" not in (body["rewritten_text"] or "")
    assert body["violations"][0]["rule_id"] == "GC-001"
