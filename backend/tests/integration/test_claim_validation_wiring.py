"""Integration proof: ClaimValidation is mounted and reachable through the public API."""

from __future__ import annotations

from typing import Any, cast

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


async def test_measure_variants_normalise_at_the_api_boundary() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        registered = await client.post(
            "/api/v1/reference-figures",
            json={
                "measure": {
                    "measure": "  Kassenstellen  ",
                    "unit": "count",
                    "period": "2026",
                    "geography": "at",
                },
                "value": "3.2",
                "tier": "official_statistics",
                "as_of": "2026-01-01",
                "source_id": "statistik_austria",
            },
        )
        assert registered.status_code == 201, registered.text
        assert registered.json()["measure"] == "kassenstellen"
        assert registered.json()["geography"] == "AT"

        verified = await client.post(
            "/api/v1/claims:verify",
            json={
                "text": "Im Jahr 2026 gibt es 3,2 Mio Kassenstellen",
                "claim_type": "quantitative",
                "measure": {
                    "measure": "KASSENSTELLEN",
                    "unit": "count",
                    "period": "2026",
                    "geography": "AT",
                },
                "asserted_value": "3.2",
            },
        )
        assert verified.status_code == 200, verified.text
        assert verified.json()["verdict"] == "verified"


async def test_contradictions_are_produced_and_idempotent() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    measure = {
        "measure": "Kontra",
        "unit": "count",
        "period": "2026",
        "geography": "AT",
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/api/v1/reference-figures",
            json={
                "measure": measure,
                "value": "3.2",
                "tier": "official_statistics",
                "as_of": "2026-01-01",
                "source_id": "stat",
            },
        )

        async def verify(value: str) -> dict[str, Any]:
            response = await client.post(
                "/api/v1/claims:verify",
                json={
                    "text": f"{value} Einheiten",
                    "claim_type": "quantitative",
                    "measure": measure,
                    "asserted_value": value,
                },
            )
            assert response.status_code == 200, response.text
            return cast(dict[str, Any], response.json())

        await verify("3.2")
        await verify("4.1")

        findings = await client.get("/api/v1/contradictions")
        assert findings.status_code == 200, findings.text
        items = findings.json()["items"]
        assert len(items) == 1
        assert items[0]["delta"] == "0.9"

        findings = await client.get("/api/v1/contradictions")
        assert len(findings.json()["items"]) == 1


async def test_compatible_claims_do_not_create_contradictions() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    measure = {
        "measure": "Kompatibel",
        "unit": "count",
        "period": "2026",
        "geography": "AT",
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/api/v1/reference-figures",
            json={
                "measure": measure,
                "value": "3.2",
                "tier": "official_statistics",
                "as_of": "2026-01-01",
                "source_id": "stat",
            },
        )
        for value in ("3.2", "3.25"):
            response = await client.post(
                "/api/v1/claims:verify",
                json={
                    "text": f"{value} Einheiten",
                    "claim_type": "quantitative",
                    "measure": measure,
                    "asserted_value": value,
                },
            )
            assert response.json()["verdict"] == "verified"

        findings = await client.get("/api/v1/contradictions")
        assert findings.json()["items"] == []


async def test_year_before_figure_is_not_turned_into_contradiction() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    measure = {
        "measure": "Jahr",
        "unit": "count",
        "period": "2026",
        "geography": "AT",
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/api/v1/reference-figures",
            json={
                "measure": measure,
                "value": "3200000",
                "tier": "official_statistics",
                "as_of": "2026-01-01",
                "source_id": "stat",
            },
        )
        response = await client.post(
            "/api/v1/claims:verify",
            json={
                "text": "Im Jahr 2026 gibt es 3.200.000 Kassenstellen",
                "claim_type": "quantitative",
                "measure": measure,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["verdict"] != "contradicted"


async def test_reference_mismatch_names_the_dimension() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/api/v1/reference-figures",
            json={
                "measure": {
                    "measure": "Periode",
                    "unit": "count",
                    "period": "2025",
                    "geography": "AT",
                },
                "value": "3.2",
                "tier": "official_statistics",
                "as_of": "2025-01-01",
                "source_id": "stat",
            },
        )
        response = await client.post(
            "/api/v1/claims:verify",
            json={
                "text": "3.2 Einheiten",
                "claim_type": "quantitative",
                "measure": {
                    "measure": "Periode",
                    "unit": "count",
                    "period": "2026",
                    "geography": "AT",
                },
                "asserted_value": "3.2",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["verdict"] == "ambiguous"

        container = app.state.claim_validation
        stored = await container.claims.get(response.json()["claim_id"])
        assert stored is not None
        assert stored.review is not None
        assert "period=2025" in stored.review.question
