"""HTTP walkthrough from an empty deployment to a published decision brief.

Canonical: ``docs/demo-walkthrough.md``

The walkthrough uses only the public API. It proves the chain end to end: seed → open run → open
round → nine evidenced positions and turns → close round → consensus derived by the subscriber →
decision brief published without a manual provenance call.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass

import httpx

DEMO_TOPIC = "Kassenstellen"
DEMO_CLAIM = "Das ASVG regelt die Kassenstellen."


@dataclass(frozen=True, slots=True)
class WalkthroughResult:
    run_id: str
    position_ids: tuple[str, ...]
    argument_ids: tuple[str, ...]
    brief_id: str
    brief_version: int

    def as_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


async def run_walkthrough(
    client: httpx.AsyncClient,
    *,
    pack_id: str,
    stakeholder_ids: list[str] | None = None,
) -> WalkthroughResult:
    """Drive the public API; every expected status is asserted, not ignored."""
    if stakeholder_ids is None:
        listed = await client.get("/api/v1/stakeholders")
        _expect(listed, 200, "list stakeholders")
        stakeholder_ids = [item["stakeholder_id"] for item in listed.json()["items"]]

    opened = await client.post(
        "/api/v1/runs",
        json={
            "question": "Wie sichern wir Kassenstellen und Versorgung in Oesterreich?",
            "round_cap": 1,
            "stakeholder_ids": stakeholder_ids,
        },
    )
    _expect(opened, 202, "open run")
    run_id = opened.json()["run_id"]

    round_opened = await client.post(f"/api/v1/runs/{run_id}/rounds")
    _expect(round_opened, 201, "open round")

    position_ids: list[str] = []
    argument_ids: list[str] = []
    for index, stakeholder in enumerate(stakeholder_ids, start=1):
        position = await client.post(
            f"/api/v1/runs/{run_id}/positions",
            json={
                "stakeholder_id": stakeholder,
                "topic": DEMO_TOPIC,
                "stance": "support",
                "proposal": {"summary": "Kassenstellen ausbauen und Versorgung sichern"},
                "evidence_ids": [pack_id],
            },
        )
        _expect(position, 201, f"position {stakeholder}")
        position_ids.append(position.json()["position_id"])

        argument = await client.post(
            f"/api/v1/runs/{run_id}/turns",
            json={
                "stakeholder_id": stakeholder,
                "target": {"topic": DEMO_TOPIC},
                "stance": "support",
                "text": "Das ASVG regelt die Kassenstellen und die Finanzierung.",
                "claims": [{"text": DEMO_CLAIM}],
                "evidence_ids": [pack_id],
                "invocation_id": f"inv_demo_{index:02d}",
            },
        )
        _expect(argument, 201, f"turn {stakeholder}")
        argument_ids.append(argument.json()["argument_id"])

    closed = await client.post(
        f"/api/v1/runs/{run_id}/rounds/1:close",
        json={"learning": [], "convergence": "none"},
    )
    _expect(closed, 200, "close round")
    if closed.json()["stopping_condition"]["name"] != "round_cap":
        raise AssertionError("demo round must close on the round cap")

    consensus = await client.get(f"/api/v1/runs/{run_id}/consensus")
    _expect(consensus, 200, "read derived consensus")
    if not consensus.json()["records"]:
        raise AssertionError("closing the run did not derive consensus rows")

    published = await client.post(f"/api/v1/runs/{run_id}/brief")
    _expect(published, 201, "publish decision brief")
    brief = published.json()

    versions = await client.get(f"/api/v1/runs/{run_id}/briefs")
    _expect(versions, 200, "list brief versions")
    if len(versions.json()["versions"]) != 1:
        raise AssertionError("the first publication must produce exactly one version")

    return WalkthroughResult(
        run_id=run_id,
        position_ids=tuple(position_ids),
        argument_ids=tuple(argument_ids),
        brief_id=brief["brief_id"],
        brief_version=brief["version"]["number"],
    )


def _expect(response: httpx.Response, status: int, step: str) -> None:
    if response.status_code != status:
        raise AssertionError(
            f"{step}: expected {status}, got {response.status_code}: {response.text}"
        )


async def _main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    pack_id = sys.argv[2] if len(sys.argv) > 2 else ""
    if not pack_id:
        raise SystemExit("usage: python -m shared.demo_walkthrough BASE_URL PACK_ID")
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        result = await run_walkthrough(client, pack_id=pack_id)
    sys.stdout.write(result.as_json() + "\n")


if __name__ == "__main__":  # pragma: no cover - operator entry
    asyncio.run(_main())
