"""Integrationstests fuer Datei-Upload-Endpunkte."""

import io

import pytest
from httpx import AsyncClient


@pytest.fixture
async def session_id(client: AsyncClient) -> str:
    """Erstellt eine Testsitzung und gibt deren ID zurueck."""
    response = await client.post("/api/sessions", json={"name": "Upload Test"})
    return response.json()["id"]


@pytest.mark.asyncio
async def test_upload_extracts_iocs(client: AsyncClient, session_id: str) -> None:
    """Prueft ob IOCs (IP und Domain) aus dem Upload-Text extrahiert werden."""
    content = "Found IP 8.8.8.8 and domain evil.example.com"
    file = io.BytesIO(content.encode())
    response = await client.post(
        f"/api/sessions/{session_id}/upload",
        files={"file": ("report.txt", file, "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["assets"]) >= 2
    types = {a["type"] for a in data["assets"]}
    assert "IP_ADDRESS" in types
    assert "DOMAIN" in types


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient, session_id: str) -> None:
    """Prueft ob eine Datei ohne IOCs eine leere Asset-Liste zurueckgibt."""
    file = io.BytesIO(b"no indicators here just text")
    response = await client.post(
        f"/api/sessions/{session_id}/upload",
        files={"file": ("empty.txt", file, "text/plain")},
    )
    assert response.status_code == 201
    assert response.json()["assets"] == []


@pytest.mark.asyncio
async def test_upload_invalid_session(client: AsyncClient) -> None:
    """Prueft ob ein Upload zu einer nicht vorhandenen Sitzung 404 zurueckgibt."""
    file = io.BytesIO(b"8.8.8.8")
    response = await client.post(
        "/api/sessions/nonexistent_session_id_00/upload",
        files={"file": ("test.txt", file, "text/plain")},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_file_too_large(client: AsyncClient, session_id: str) -> None:
    """Prueft ob eine zu grosse Datei einen 413-Fehler ausloest."""
    large_content = b"8.8.8.8 " * (11 * 1024 * 1024 // 8)
    file = io.BytesIO(large_content)
    response = await client.post(
        f"/api/sessions/{session_id}/upload",
        files={"file": ("big.txt", file, "text/plain")},
    )
    assert response.status_code == 413
