"""Integration: the demo chain publishes a brief with no manual provenance ceremony."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from shared.app import create_app
from shared.config import Settings
from shared.demo_seed import seed_demo
from shared.demo_walkthrough import DEMO_CLAIM, DEMO_TOPIC, run_walkthrough
from shared.enums import AuthMode, Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def _app() -> FastAPI:
    return create_app(
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            persistence=Persistence.MEMORY,
            auth_mode=AuthMode.DEMO,
        )
    )


async def _client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def demo_client() -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient, str]]:
    app = _app()
    seed = await seed_demo(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield app, client, seed.pack_ids["kassenstellen"]
    await app.state.db.dispose()


def test_seed_cli_keeps_stdout_parseable_at_default_log_level() -> None:
    backend = Path(__file__).resolve().parents[2]
    env = {
        **os.environ,
        "ENV": "local",
        "AUTH_MODE": "demo",
        "PERSISTENCE": "memory",
        "DATABASE_URL": DATABASE_URL,
        "LOG_LEVEL": "INFO",
        "LLM_PROVIDER": "scripted",
    }
    completed = subprocess.run(
        [sys.executable, "-m", "shared.demo_seed"],
        cwd=backend,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["snapshot_id"].startswith("snp_")
    assert completed.stderr  # structured logs went to stderr, not the JSON file


async def test_seed_is_idempotent_in_the_memory_family() -> None:
    app = _app()
    try:
        first = await seed_demo(app)
        second = await seed_demo(app)
    finally:
        await app.state.db.dispose()

    assert first.document_id == second.document_id
    assert first.snapshot_id == second.snapshot_id
    assert first.pack_ids == second.pack_ids
    assert sorted(first.figure_ids) == sorted(second.figure_ids)


async def test_seeded_chain_publishes_a_brief_without_manual_provenance(
    demo_client: tuple[FastAPI, httpx.AsyncClient, str],
) -> None:
    _, client, pack_id = demo_client

    result = await run_walkthrough(client, pack_id=pack_id)

    assert result.brief_version == 1
    provenance = await client.get(f"/api/v1/positions/{result.position_ids[0]}/provenance")
    assert provenance.status_code == 200, provenance.text
    assert provenance.json()["argument_ids"]
    assert provenance.json()["invocation_id"].startswith("inv_demo_")


async def test_revised_position_is_disclosed_again_and_the_brief_uses_it(
    demo_client: tuple[FastAPI, httpx.AsyncClient, str],
) -> None:
    app, client, pack_id = demo_client
    run_id, position_id, argument_id = await _one_stakeholder_run(client, pack_id)

    revised = await client.post(
        f"/api/v1/runs/{run_id}/positions/{position_id}:revise",
        json={
            "stance": "conditional_accept",
            "reason": {"argument_ids": [argument_id], "pack_ids": [], "driver": "new evidence"},
        },
    )
    assert revised.status_code == 200, revised.text
    revised_id = revised.json()["position_id"]
    assert revised_id != position_id

    closed = await client.post(
        f"/api/v1/runs/{run_id}/rounds/1:close",
        json={"learning": [], "convergence": "none"},
    )
    assert closed.status_code == 200, closed.text

    provenance = await client.get(f"/api/v1/positions/{revised_id}/provenance")
    assert provenance.status_code == 200, provenance.text
    assert provenance.json()["evidence_ids"]

    published = await client.post(f"/api/v1/runs/{run_id}/brief")
    assert published.status_code == 201, published.text
    assert published.json()["version"]["number"] == 1
    assert app.state.governance_provenance_producer == "close_round"


async def test_brief_stays_fail_closed_when_the_provenance_store_is_emptied(
    demo_client: tuple[FastAPI, httpx.AsyncClient, str],
) -> None:
    app, client, pack_id = demo_client
    run_id, position_id, _ = await _one_stakeholder_run(client, pack_id)
    closed = await client.post(
        f"/api/v1/runs/{run_id}/rounds/1:close",
        json={"learning": [], "convergence": "none"},
    )
    assert closed.status_code == 200, closed.text

    store = app.state.governance_compliance.disclose_position_provenance._store
    store._rows.clear()
    assert (await client.get(f"/api/v1/positions/{position_id}/provenance")).status_code == 404

    refused = await client.post(f"/api/v1/runs/{run_id}/brief")
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "DISCLOSURE_MISSING"


async def _one_stakeholder_run(client: httpx.AsyncClient, pack_id: str) -> tuple[str, str, str]:
    opened = await client.post(
        "/api/v1/runs",
        json={
            "question": "Kassenstellen sichern",
            "round_cap": 1,
            "stakeholder_ids": ["stk_aerztekammer"],
        },
    )
    assert opened.status_code == 202, opened.text
    run_id = opened.json()["run_id"]
    assert (await client.post(f"/api/v1/runs/{run_id}/rounds")).status_code == 201
    position = await client.post(
        f"/api/v1/runs/{run_id}/positions",
        json={
            "stakeholder_id": "stk_aerztekammer",
            "topic": DEMO_TOPIC,
            "stance": "support",
            "proposal": {"summary": "Kassenstellen ausbauen"},
            "evidence_ids": [pack_id],
        },
    )
    assert position.status_code == 201, position.text
    argument = await client.post(
        f"/api/v1/runs/{run_id}/turns",
        json={
            "stakeholder_id": "stk_aerztekammer",
            "target": {"topic": DEMO_TOPIC},
            "stance": "support",
            "text": "Das ASVG regelt die Kassenstellen und die Finanzierung.",
            "claims": [{"text": DEMO_CLAIM}],
            "evidence_ids": [pack_id],
            "invocation_id": "inv_demo_single",
        },
    )
    assert argument.status_code == 201, argument.text
    return run_id, position.json()["position_id"], argument.json()["argument_id"]
