"""Gemeinsame Test-Fixtures fuer die Middleware-API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Test-HTTP-Client mit ASGI-Transport fuer direkten App-Zugriff."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
