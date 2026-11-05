"""Integration proof: ClaimValidation is mounted and reachable through the public API."""

from __future__ import annotations

import httpx

from claim_validation.interfaces.published import ClaimVerdictView
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


def _measure() -> dict[str, str]:
    return {"measure": "Kassenstellen", "unit": "count", "period": "2026", "geography": "AT"}


async def test_claim_verification_survives_the_public_api() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        registered = await client.post(
            "/api/v1/reference-figures",
            json={
                "measure": _measure(),
                "value": "3.2",
                "tier": "official_statistics",
                "as_of": "2026-01-01",
                "source_id": "statistik_austria",
            },
        )
        assert registered.status_code == 201, registered.text
        assert registered.json()["figure_id"].startswith("fig_")

        verified = await client.post(
            "/api/v1/claims:verify",
            json={
                "text": "Es gibt 3,2 Mrd. Kassenstellen",
                "claim_type": "quantitative",
                "measure": _measure(),
                "asserted_value": "3.2",
            },
        )
        assert verified.status_code == 200, verified.text
        assert verified.json()["verdict"] == "verified"
        claim_id = verified.json()["claim_id"]

        detail = await client.get(f"/api/v1/claims/{claim_id}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["verdict"] == "verified"
        assert detail.json()["sources"] == ["statistik_austria"]

        ambiguous = await client.post(
            "/api/v1/claims:verify",
            json={
                "text": "Die Wartezeit betraegt 12 Tage",
                "claim_type": "quantitative",
                "measure": {
                    "measure": "Wartezeit",
                    "unit": "days",
                    "period": "2026",
                    "geography": "AT",
                },
                "asserted_value": "12",
            },
        )
        assert ambiguous.status_code == 200, ambiguous.text
        assert ambiguous.json()["verdict"] == "ambiguous"

        unsupported = await client.post(
            "/api/v1/claims:verify",
            json={"text": "Das ist gesetzlich verboten", "claim_type": "legal"},
        )
        assert unsupported.status_code == 200, unsupported.text
        assert unsupported.json()["verdict"] == "unsupported"
        unsupported_id = unsupported.json()["claim_id"]

        retained = await client.get(f"/api/v1/claims/{unsupported_id}")
        assert retained.status_code == 200, retained.text
        assert retained.json()["verdict"] == "unsupported"

        qualitative = await client.post(
            "/api/v1/claims:verify",
            json={"text": "Die Stimmung ist angespannt", "claim_type": "qualitative"},
        )
        assert qualitative.status_code == 200, qualitative.text
        assert qualitative.json()["verdict"] == "ambiguous"

        figures = await client.get("/api/v1/reference-figures")
        assert figures.status_code == 200, figures.text
        assert len(figures.json()["items"]) == 1

        contradictions = await client.get("/api/v1/contradictions")
        assert contradictions.status_code == 200, contradictions.text
        assert contradictions.json()["items"] == []

        press = await client.post(
            "/api/v1/reference-figures",
            json={
                "measure": _measure(),
                "value": "4.1",
                "tier": "press_report",
                "as_of": "2026-01-01",
                "source_id": "newspaper",
            },
        )
        assert press.status_code == 422, press.text
        assert press.json()["code"] == "REFERENCE_FIGURE_NOT_AUTHORITATIVE"

        resolved = await client.post(
            f"/api/v1/claims/{ambiguous.json()['claim_id']}/reviews",
            json={"verdict": "verified", "basis": "expert confirmed the figure"},
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["verdict"] == "verified"


def test_verdict_view_is_free_of_internal_state() -> None:
    assert ClaimVerdictView.__dataclass_fields__.keys() == {
        "claim_id",
        "verdict",
        "claim_type",
        "sources",
        "delta",
    }
