"""Integration tests for DLP management endpoints."""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestInternalNetworks:
    """Tests for /api/dlp/networks CRUD endpoints."""

    async def test_create_network(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/dlp/networks",
            json={"cidr": "10.0.0.0/8", "label": "Private range"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["cidr"] == "10.0.0.0/8"
        assert data["label"] == "Private range"
        assert "id" in data

    async def test_list_networks(self, client: AsyncClient) -> None:
        await client.post(
            "/api/dlp/networks",
            json={"cidr": "172.16.0.0/12"},
        )
        response = await client.get("/api/dlp/networks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    async def test_delete_network(self, client: AsyncClient) -> None:
        create_resp = await client.post(
            "/api/dlp/networks",
            json={"cidr": "192.168.0.0/16"},
        )
        network_id = create_resp.json()["id"]
        delete_resp = await client.delete(f"/api/dlp/networks/{network_id}")
        assert delete_resp.status_code == 204

    async def test_delete_nonexistent_network_returns_404(self, client: AsyncClient) -> None:
        response = await client.delete("/api/dlp/networks/00000000000000000000000000")
        assert response.status_code == 404

    async def test_create_duplicate_network_returns_409(self, client: AsyncClient) -> None:
        await client.post("/api/dlp/networks", json={"cidr": "10.10.0.0/16"})
        response = await client.post("/api/dlp/networks", json={"cidr": "10.10.0.0/16"})
        assert response.status_code == 409


class TestInternalDomains:
    """Tests for /api/dlp/domains CRUD endpoints."""

    async def test_create_domain(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/dlp/domains",
            json={"domain": "Company.COM", "label": "Corporate domain"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["domain"] == "company.com"
        assert data["label"] == "Corporate domain"

    async def test_list_domains(self, client: AsyncClient) -> None:
        await client.post("/api/dlp/domains", json={"domain": "internal.net"})
        response = await client.get("/api/dlp/domains")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    async def test_delete_domain(self, client: AsyncClient) -> None:
        create_resp = await client.post(
            "/api/dlp/domains", json={"domain": "test-delete.com"}
        )
        domain_id = create_resp.json()["id"]
        delete_resp = await client.delete(f"/api/dlp/domains/{domain_id}")
        assert delete_resp.status_code == 204

    async def test_delete_nonexistent_domain_returns_404(self, client: AsyncClient) -> None:
        response = await client.delete("/api/dlp/domains/00000000000000000000000000")
        assert response.status_code == 404

    async def test_create_duplicate_domain_returns_409(self, client: AsyncClient) -> None:
        await client.post("/api/dlp/domains", json={"domain": "duplicate.com"})
        response = await client.post("/api/dlp/domains", json={"domain": "duplicate.com"})
        assert response.status_code == 409


class TestDlpRefresh:
    """Tests for POST /api/dlp/refresh endpoint."""

    async def test_refresh_returns_204(self, client: AsyncClient) -> None:
        response = await client.post("/api/dlp/refresh")
        assert response.status_code == 204
