"""Integrationstests fuer Session-Endpunkte."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient) -> None:
    """Prueft ob eine neue Sitzung korrekt angelegt wird."""
    response = await client.post("/api/sessions", json={"name": "Test Session"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Session"
    assert len(data["id"]) == 26  # ULID-Laenge


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient) -> None:
    """Prueft ob die Sitzungsliste mindestens eine Sitzung enthaelt."""
    await client.post("/api/sessions", json={"name": "Session 1"})
    response = await client.get("/api/sessions")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_create_session_missing_name(client: AsyncClient) -> None:
    """Prueft ob fehlendes Name-Feld einen Validierungsfehler ausloest."""
    response = await client.post("/api/sessions", json={})
    assert response.status_code == 422
