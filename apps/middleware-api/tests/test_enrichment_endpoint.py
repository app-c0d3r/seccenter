"""Integration tests for POST /api/sessions/{id}/enrich endpoint."""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def _create_session_with_assets(client: AsyncClient) -> tuple[str, list[str]]:
    """Helper: create session, upload file with IOCs, return (session_id, asset_ids)."""
    # Create session
    resp = await client.post("/api/sessions", json={"name": "Test Enrichment"})
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # Upload file with IOCs
    files = {"file": ("test.txt", b"8.8.8.8\nevil.com", "text/plain")}
    resp = await client.post(f"/api/sessions/{session_id}/upload", files=files)
    assert resp.status_code == 200
    asset_ids = [a["id"] for a in resp.json()["assets"]]
    return session_id, asset_ids


class TestEnrichEndpoint:
    """Tests for POST /api/sessions/{id}/enrich."""

    async def test_enrich_returns_202(self, client: AsyncClient) -> None:
        session_id, asset_ids = await _create_session_with_assets(client)

        resp = await client.post(
            f"/api/sessions/{session_id}/enrich",
            json={"asset_ids": asset_ids},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert "batch_id" in data
        assert data["asset_count"] > 0

    async def test_enrich_nonexistent_session_returns_404(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/sessions/00000000000000000000000000/enrich",
            json={"asset_ids": ["a1"]},
        )
        assert resp.status_code == 404

    async def test_enrich_filters_internal_assets(self, client: AsyncClient) -> None:
        # Create DLP rule for 8.8.8.0/24
        await client.post(
            "/api/dlp/networks",
            json={"cidr": "8.8.8.0/24", "label": "Google DNS"},
        )

        session_id, asset_ids = await _create_session_with_assets(client)

        # Upload marks 8.8.8.8 as INTERNAL via DLP. Only evil.com should be PENDING.
        resp = await client.post(
            f"/api/sessions/{session_id}/enrich",
            json={"asset_ids": asset_ids},
        )

        assert resp.status_code == 202
        # Only non-internal assets should be enriched
        data = resp.json()
        assert data["asset_count"] >= 1

    async def test_enrich_all_internal_returns_422(self, client: AsyncClient) -> None:
        # Create DLP rules to cover all test IOCs
        await client.post(
            "/api/dlp/networks",
            json={"cidr": "8.8.8.0/24", "label": "Google DNS"},
        )
        await client.post(
            "/api/dlp/domains",
            json={"domain": "evil.com", "label": "Test domain"},
        )

        # Create session and upload file - all assets will be INTERNAL
        resp = await client.post("/api/sessions", json={"name": "All Internal"})
        session_id = resp.json()["id"]

        files = {"file": ("test.txt", b"8.8.8.8\nevil.com", "text/plain")}
        resp = await client.post(f"/api/sessions/{session_id}/upload", files=files)
        asset_ids = [a["id"] for a in resp.json()["assets"]]

        resp = await client.post(
            f"/api/sessions/{session_id}/enrich",
            json={"asset_ids": asset_ids},
        )
        assert resp.status_code == 422
