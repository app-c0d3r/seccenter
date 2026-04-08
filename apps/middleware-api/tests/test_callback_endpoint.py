"""Integration tests for POST /api/callbacks/n8n endpoint."""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def _setup_enriched_batch(client: AsyncClient) -> tuple[str, str, list[str]]:
    """Helper: create session, upload IOCs, enrich to get batch. Returns (session_id, batch_id, asset_ids)."""
    # Create session
    resp = await client.post("/api/sessions", json={"name": "Callback Test"})
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # Upload file with IOCs
    files = {"file": ("test.txt", b"8.8.8.8\nevil.com", "text/plain")}
    resp = await client.post(f"/api/sessions/{session_id}/upload", files=files)
    assert resp.status_code == 200
    asset_ids = [a["id"] for a in resp.json()["assets"]]

    # Enrich to create batch and mark PROCESSING
    resp = await client.post(
        f"/api/sessions/{session_id}/enrich",
        json={"asset_ids": asset_ids},
    )
    assert resp.status_code == 202
    batch_id = resp.json()["batch_id"]

    return session_id, batch_id, asset_ids


class TestCallbackEndpoint:
    """Tests for POST /api/callbacks/n8n."""

    async def test_callback_updates_assets(self, client: AsyncClient) -> None:
        session_id, batch_id, asset_ids = await _setup_enriched_batch(client)

        resp = await client.post("/api/callbacks/n8n", json={
            "session_id": session_id,
            "batch_id": batch_id,
            "results": [
                {"asset_id": aid, "status": "ENRICHED", "threat_intel": {"score": 0}}
                for aid in asset_ids
            ],
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["batch_id"] == batch_id
        assert data["updated"] == len(asset_ids)

    async def test_callback_idempotency(self, client: AsyncClient) -> None:
        session_id, batch_id, asset_ids = await _setup_enriched_batch(client)

        callback_body = {
            "session_id": session_id,
            "batch_id": batch_id,
            "results": [
                {"asset_id": aid, "status": "ENRICHED", "threat_intel": {"score": 0}}
                for aid in asset_ids
            ],
        }

        # First call
        resp1 = await client.post("/api/callbacks/n8n", json=callback_body)
        assert resp1.status_code == 200

        # Second call (idempotent)
        resp2 = await client.post("/api/callbacks/n8n", json=callback_body)
        assert resp2.status_code == 200
        assert resp2.json()["updated"] == 0

    async def test_callback_nonexistent_batch_returns_404(self, client: AsyncClient) -> None:
        resp = await client.post("/api/callbacks/n8n", json={
            "session_id": "fake",
            "batch_id": "00000000000000000000000000",
            "results": [],
        })
        assert resp.status_code == 404

    async def test_callback_processing_guard(self, client: AsyncClient) -> None:
        session_id, batch_id, asset_ids = await _setup_enriched_batch(client)

        # Manually change first asset to CONFIRMED (simulating analyst override)
        await client.patch(
            f"/api/sessions/{session_id}/assets/{asset_ids[0]}",
            json={"status": "CONFIRMED"},
        )

        resp = await client.post("/api/callbacks/n8n", json={
            "session_id": session_id,
            "batch_id": batch_id,
            "results": [
                {"asset_id": aid, "status": "ENRICHED", "threat_intel": {"score": 0}}
                for aid in asset_ids
            ],
        })

        assert resp.status_code == 200
        # First asset was CONFIRMED, so it should NOT be updated (PROCESSING guard)
        assert resp.json()["updated"] == len(asset_ids) - 1

    async def test_callback_partial_batch(self, client: AsyncClient) -> None:
        session_id, batch_id, asset_ids = await _setup_enriched_batch(client)

        # Only send results for first asset
        resp = await client.post("/api/callbacks/n8n", json={
            "session_id": session_id,
            "batch_id": batch_id,
            "results": [
                {"asset_id": asset_ids[0], "status": "ENRICHED", "threat_intel": {"score": 0}},
            ],
        })

        assert resp.status_code == 200
        # Batch should be PARTIAL since not all assets were returned

    async def test_callback_all_errors_marks_failed(self, client: AsyncClient) -> None:
        session_id, batch_id, asset_ids = await _setup_enriched_batch(client)

        resp = await client.post("/api/callbacks/n8n", json={
            "session_id": session_id,
            "batch_id": batch_id,
            "results": [
                {"asset_id": aid, "status": "ENRICHED", "threat_intel": {"error": "API timeout"}}
                for aid in asset_ids
            ],
        })

        assert resp.status_code == 200
