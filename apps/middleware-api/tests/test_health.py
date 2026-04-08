"""Integrationstest fuer den Health-Endpunkt."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """Prueft ob der Health-Endpunkt 'ok' zurueckgibt."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
