# Phase 2A: DLP Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic DLP layer that classifies IOCs as INTERNAL or PENDING before persistence, blocking internal assets from external enrichment APIs.

**Architecture:** In-memory DlpClassifier singleton loads CIDR blocks and domains from PostgreSQL at startup. Upload flow calls `classify()` between extraction and persistence. CRUD endpoints manage DLP rules, explicit refresh endpoint reloads cache.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (AsyncSession), Pydantic v2, PostgreSQL 16 (native CIDR type), pytest + httpx

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `infrastructure/db/init.sql` | Modify | Add 4 enum values, `internal_networks` table, `internal_domains` table |
| `apps/middleware-api/app/services/dlp_classifier.py` | Create | DlpCache dataclass, DlpClassifier with classify/load/refresh |
| `apps/middleware-api/app/schemas/dlp.py` | Create | Pydantic models for DLP CRUD |
| `apps/middleware-api/app/schemas/asset.py` | Modify | Extend AssetStatus enum with 4 new values |
| `apps/middleware-api/app/db/models.py` | Modify | Add InternalNetworkModel, InternalDomainModel, extend asset_status enum |
| `apps/middleware-api/app/db/repository.py` | Modify | Add DLP CRUD functions |
| `apps/middleware-api/app/router/dlp.py` | Create | CRUD + refresh endpoints |
| `apps/middleware-api/app/router/uploads.py` | Modify | Add DlpClassifier dependency + classify() call |
| `apps/middleware-api/app/main.py` | Modify | Include DLP router, load DLP cache in lifespan |
| `apps/web-ui/src/types/index.ts` | Modify | Extend AssetStatus union |
| `apps/web-ui/src/components/AssetTable.tsx` | Modify | Add new status values to dropdown, color-code INTERNAL |
| `apps/middleware-api/tests/test_dlp_classifier.py` | Create | Unit tests for classifier logic |
| `apps/middleware-api/tests/test_dlp_routes.py` | Create | Integration tests for DLP endpoints |

---

### Task 1: Extend PostgreSQL Schema

**Files:**
- Modify: `infrastructure/db/init.sql:22-26` (asset_status enum)
- Modify: `infrastructure/db/init.sql` (append new tables)

- [ ] **Step 1: Extend asset_status enum and add DLP tables in init.sql**

Replace the existing `asset_status` enum and append two new tables at the end of the file. The full updated `init.sql`:

```sql
-- PostgreSQL Initialisierungsschema fuer SECCENTER Phase 2A
-- Erstellt die Datenbankerweiterungen, Typen und Tabellen


-- Tabelle fuer Analyse-Sitzungen
CREATE TABLE sessions (
    id   CHAR(26)     PRIMARY KEY,       -- ULID (26 Zeichen)
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Aufzaehlungstyp fuer Asset-Kategorien
CREATE TYPE asset_type AS ENUM (
    'IP_ADDRESS',
    'DOMAIN',
    'FILE_HASH_MD5',
    'FILE_HASH_SHA1',
    'FILE_HASH_SHA256'
);

-- Aufzaehlungstyp fuer Bearbeitungsstatus eines Assets (vollstaendiger Lifecycle)
CREATE TYPE asset_status AS ENUM (
    'PENDING',
    'INTERNAL',
    'PROCESSING',
    'ENRICHED',
    'CRITICAL',
    'CONFIRMED',
    'IGNORED'
);

-- Tabelle fuer sicherheitsrelevante Assets einer Sitzung
CREATE TABLE assets (
    id         CHAR(26)     PRIMARY KEY,
    session_id CHAR(26)     REFERENCES sessions(id) ON DELETE CASCADE,
    value      TEXT         NOT NULL,
    type       asset_type   NOT NULL,
    status     asset_status DEFAULT 'PENDING',
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

-- Index fuer schnelle Suche nach Sitzungs-ID
CREATE INDEX idx_assets_session ON assets(session_id);

-- DLP: Interne Netzwerke (CIDR-Bloecke)
CREATE TABLE internal_networks (
    id         CHAR(26)     PRIMARY KEY,
    cidr       CIDR         NOT NULL,
    label      VARCHAR(255),
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_internal_networks_cidr ON internal_networks(cidr);

-- DLP: Interne Domains
CREATE TABLE internal_domains (
    id         CHAR(26)     PRIMARY KEY,
    domain     VARCHAR(255) NOT NULL,
    label      VARCHAR(255),
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_internal_domains_domain ON internal_domains(domain);
```

- [ ] **Step 2: Commit**

```bash
git add infrastructure/db/init.sql
git commit -m "feat: extend PostgreSQL schema for DLP (Phase 2A)"
```

---

### Task 2: Extend Asset Status Enums (Backend + Frontend)

**Files:**
- Modify: `apps/middleware-api/app/schemas/asset.py:19-24`
- Modify: `apps/middleware-api/app/db/models.py:64-74`
- Modify: `apps/web-ui/src/types/index.ts:15`
- Modify: `apps/web-ui/src/components/AssetTable.tsx:89-103`

- [ ] **Step 1: Extend Python AssetStatus enum in `apps/middleware-api/app/schemas/asset.py`**

Replace the `AssetStatus` class (lines 19-24):

```python
class AssetStatus(str, Enum):
    """Moegliche Verarbeitungszustaende eines Assets."""

    PENDING = "PENDING"
    INTERNAL = "INTERNAL"
    PROCESSING = "PROCESSING"
    ENRICHED = "ENRICHED"
    CRITICAL = "CRITICAL"
    CONFIRMED = "CONFIRMED"
    IGNORED = "IGNORED"
```

- [ ] **Step 2: Extend SQLAlchemy asset_status enum in `apps/middleware-api/app/db/models.py`**

Replace the status column definition (lines 64-74):

```python
    # Verarbeitungsstatus
    status: Mapped[str] = mapped_column(
        Enum(
            "PENDING",
            "INTERNAL",
            "PROCESSING",
            "ENRICHED",
            "CRITICAL",
            "CONFIRMED",
            "IGNORED",
            name="asset_status",
            create_type=False,
        ),
        server_default="PENDING",
        nullable=False,
    )
```

- [ ] **Step 3: Extend TypeScript AssetStatus in `apps/web-ui/src/types/index.ts`**

Replace line 15:

```typescript
/** Status eines analysierten Assets im Workflow */
export type AssetStatus =
  | "PENDING"
  | "INTERNAL"
  | "PROCESSING"
  | "ENRICHED"
  | "CRITICAL"
  | "CONFIRMED"
  | "IGNORED";
```

- [ ] **Step 4: Update AssetTable status dropdown in `apps/web-ui/src/components/AssetTable.tsx`**

Replace the Select component in the status column cell (lines 89-103). INTERNAL assets should be read-only (blocked by DLP), other statuses are analyst-editable:

```tsx
    columnHelper.accessor("status", {
      header: "Status",
      cell: (info) => {
        const asset = info.row.original;
        const sessionId = activeSessionId ?? "";

        // INTERNAL assets are DLP-blocked and cannot be changed by analysts
        if (asset.status === "INTERNAL") {
          return (
            <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700">
              INTERNAL
            </span>
          );
        }

        // Non-editable statuses set by the system
        if (["PROCESSING", "ENRICHED", "CRITICAL"].includes(asset.status)) {
          return (
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
              {asset.status}
            </span>
          );
        }

        return (
          <Select
            value={asset.status}
            onValueChange={(value: string) =>
              void handleStatusChange(sessionId, asset.id, value as AssetStatus)
            }
          >
            <SelectTrigger className="h-7 w-32 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="PENDING">PENDING</SelectItem>
              <SelectItem value="CONFIRMED">CONFIRMED</SelectItem>
              <SelectItem value="IGNORED">IGNORED</SelectItem>
            </SelectContent>
          </Select>
        );
      },
    }),
```

- [ ] **Step 5: Commit**

```bash
git add apps/middleware-api/app/schemas/asset.py apps/middleware-api/app/db/models.py apps/web-ui/src/types/index.ts apps/web-ui/src/components/AssetTable.tsx
git commit -m "feat: extend AssetStatus enum across backend and frontend"
```

---

### Task 3: DlpClassifier Service (TDD)

**Files:**
- Create: `apps/middleware-api/tests/test_dlp_classifier.py`
- Create: `apps/middleware-api/app/services/dlp_classifier.py`

- [ ] **Step 1: Write failing tests for DlpClassifier**

Create `apps/middleware-api/tests/test_dlp_classifier.py`:

```python
"""Unit tests for the DLP classifier service."""

import ipaddress

import pytest

from app.services.dlp_classifier import DlpCache, DlpClassifier


class TestIsInternalIp:
    """Tests for IP address classification against CIDR blocks."""

    def setup_method(self) -> None:
        self.classifier = DlpClassifier()
        self.classifier._cache = DlpCache(
            networks=[
                ipaddress.ip_network("10.0.0.0/8"),
                ipaddress.ip_network("192.168.1.0/24"),
            ],
            domains=set(),
        )

    def test_ip_in_private_range_is_internal(self) -> None:
        assert self.classifier.is_internal_ip("10.0.0.1") is True

    def test_ip_in_specific_subnet_is_internal(self) -> None:
        assert self.classifier.is_internal_ip("192.168.1.100") is True

    def test_ip_outside_all_ranges_is_not_internal(self) -> None:
        assert self.classifier.is_internal_ip("8.8.8.8") is False

    def test_ip_in_adjacent_subnet_is_not_internal(self) -> None:
        assert self.classifier.is_internal_ip("192.168.2.1") is False

    def test_malformed_ip_returns_false(self) -> None:
        assert self.classifier.is_internal_ip("not-an-ip") is False

    def test_empty_string_returns_false(self) -> None:
        assert self.classifier.is_internal_ip("") is False


class TestIsInternalDomain:
    """Tests for domain classification with suffix matching."""

    def setup_method(self) -> None:
        self.classifier = DlpClassifier()
        self.classifier._cache = DlpCache(
            networks=[],
            domains={"company.com", "internal.net"},
        )

    def test_exact_match_is_internal(self) -> None:
        assert self.classifier.is_internal_domain("company.com") is True

    def test_subdomain_matches_parent(self) -> None:
        assert self.classifier.is_internal_domain("api.company.com") is True

    def test_deep_subdomain_matches_parent(self) -> None:
        assert self.classifier.is_internal_domain("staging.api.company.com") is True

    def test_unrelated_domain_is_not_internal(self) -> None:
        assert self.classifier.is_internal_domain("google.com") is False

    def test_partial_name_does_not_match(self) -> None:
        """evilcompany.com should NOT match company.com."""
        assert self.classifier.is_internal_domain("evilcompany.com") is False

    def test_case_insensitive_matching(self) -> None:
        assert self.classifier.is_internal_domain("API.Company.COM") is True

    def test_second_domain_matches(self) -> None:
        assert self.classifier.is_internal_domain("mail.internal.net") is True


class TestClassify:
    """Tests for the full classify() pipeline."""

    def setup_method(self) -> None:
        self.classifier = DlpClassifier()
        self.classifier._cache = DlpCache(
            networks=[ipaddress.ip_network("10.0.0.0/8")],
            domains={"company.com"},
        )

    def test_internal_ip_gets_internal_status(self) -> None:
        iocs = [{"type": "IP_ADDRESS", "value": "10.1.2.3"}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "INTERNAL"

    def test_external_ip_gets_pending_status(self) -> None:
        iocs = [{"type": "IP_ADDRESS", "value": "8.8.8.8"}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "PENDING"

    def test_internal_domain_gets_internal_status(self) -> None:
        iocs = [{"type": "DOMAIN", "value": "api.company.com"}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "INTERNAL"

    def test_external_domain_gets_pending_status(self) -> None:
        iocs = [{"type": "DOMAIN", "value": "evil.com"}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "PENDING"

    def test_hash_always_gets_pending_status(self) -> None:
        iocs = [{"type": "FILE_HASH_SHA256", "value": "a" * 64}]
        result = self.classifier.classify(iocs)
        assert result[0]["status"] == "PENDING"

    def test_mixed_iocs_classified_correctly(self) -> None:
        iocs = [
            {"type": "IP_ADDRESS", "value": "10.0.0.1"},
            {"type": "IP_ADDRESS", "value": "1.1.1.1"},
            {"type": "DOMAIN", "value": "api.company.com"},
            {"type": "DOMAIN", "value": "google.com"},
            {"type": "FILE_HASH_MD5", "value": "d" * 32},
        ]
        result = self.classifier.classify(iocs)
        assert [r["status"] for r in result] == [
            "INTERNAL", "PENDING", "INTERNAL", "PENDING", "PENDING"
        ]

    def test_empty_list_returns_empty(self) -> None:
        assert self.classifier.classify([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/middleware-api && python -m pytest tests/test_dlp_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.dlp_classifier'`

- [ ] **Step 3: Implement DlpClassifier**

Create `apps/middleware-api/app/services/dlp_classifier.py`:

```python
"""DLP Classifier: deterministic classification of IOCs as internal or external."""

import ipaddress
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class DlpCache:
    """Immutable snapshot of DLP rules loaded from the database."""

    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = field(
        default_factory=list
    )
    domains: set[str] = field(default_factory=set)


class DlpClassifier:
    """Classifies IOCs as INTERNAL or PENDING based on cached DLP rules."""

    def __init__(self) -> None:
        self._cache = DlpCache()

    async def load(self, db: AsyncSession) -> None:
        """Load DLP rules from DB. Called at startup and on POST /api/dlp/refresh."""
        # Load internal CIDR blocks
        network_rows = await db.execute(
            text("SELECT cidr FROM internal_networks")
        )
        networks = [
            ipaddress.ip_network(str(row[0]), strict=False)
            for row in network_rows.fetchall()
        ]

        # Load internal domains (already lowercase in DB)
        domain_rows = await db.execute(
            text("SELECT domain FROM internal_domains")
        )
        domains = {str(row[0]) for row in domain_rows.fetchall()}

        # Atomic swap (GIL-safe reference assignment)
        self._cache = DlpCache(networks=networks, domains=domains)

    def is_internal_ip(self, ip: str) -> bool:
        """Check if IP falls within any internal CIDR block."""
        try:
            addr = ipaddress.ip_address(ip)
            return any(addr in net for net in self._cache.networks)
        except ValueError:
            return False

    def is_internal_domain(self, domain: str) -> bool:
        """Suffix match: api.staging.company.com matches company.com."""
        domain = domain.lower()
        parts = domain.split(".")
        for i in range(len(parts)):
            candidate = ".".join(parts[i:])
            if candidate in self._cache.domains:
                return True
        return False

    def classify(self, iocs: list[dict]) -> list[dict]:
        """Tag each IOC with status based on DLP rules.

        IP_ADDRESS and DOMAIN types are checked. Hashes always get PENDING.
        """
        for ioc in iocs:
            if ioc["type"] == "IP_ADDRESS" and self.is_internal_ip(ioc["value"]):
                ioc["status"] = "INTERNAL"
            elif ioc["type"] == "DOMAIN" and self.is_internal_domain(ioc["value"]):
                ioc["status"] = "INTERNAL"
            else:
                ioc["status"] = "PENDING"
        return iocs


# Module-level singleton
dlp_classifier = DlpClassifier()


def get_dlp_classifier() -> DlpClassifier:
    """FastAPI dependency: returns the DLP classifier singleton."""
    return dlp_classifier
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/middleware-api && python -m pytest tests/test_dlp_classifier.py -v`
Expected: All 18 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/middleware-api/app/services/dlp_classifier.py apps/middleware-api/tests/test_dlp_classifier.py
git commit -m "feat: DlpClassifier service with TDD unit tests"
```

---

### Task 4: DLP Database Models and Repository

**Files:**
- Modify: `apps/middleware-api/app/db/models.py`
- Modify: `apps/middleware-api/app/db/repository.py`

- [ ] **Step 1: Add InternalNetworkModel and InternalDomainModel to `apps/middleware-api/app/db/models.py`**

Append after the `AssetModel` class (after line 89):

```python


class InternalNetworkModel(Base):
    """Database table for internal CIDR blocks (DLP rules)."""

    __tablename__ = "internal_networks"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    cidr: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InternalDomainModel(Base):
    """Database table for internal domains (DLP rules)."""

    __tablename__ = "internal_domains"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

- [ ] **Step 2: Add DLP CRUD functions to `apps/middleware-api/app/db/repository.py`**

Add imports and functions at the end of the file. First, add `InternalDomainModel, InternalNetworkModel` to the import from `app.db.models` (line 7):

```python
from app.db.models import AssetModel, InternalDomainModel, InternalNetworkModel, SessionModel
```

Then append these functions after `update_asset_status`:

```python


async def create_internal_network(
    db: AsyncSession, network_id: str, cidr: str, label: str | None
) -> InternalNetworkModel:
    """Create a new internal network CIDR block."""
    network = InternalNetworkModel(id=network_id, cidr=cidr, label=label)
    db.add(network)
    await db.commit()
    await db.refresh(network)
    return network


async def list_internal_networks(db: AsyncSession) -> list[InternalNetworkModel]:
    """List all internal networks ordered by creation date."""
    result = await db.execute(
        select(InternalNetworkModel).order_by(InternalNetworkModel.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_internal_network(db: AsyncSession, network_id: str) -> bool:
    """Delete an internal network. Returns True if deleted, False if not found."""
    result = await db.execute(
        select(InternalNetworkModel).where(InternalNetworkModel.id == network_id)
    )
    network = result.scalar_one_or_none()
    if network is None:
        return False
    await db.delete(network)
    await db.commit()
    return True


async def create_internal_domain(
    db: AsyncSession, domain_id: str, domain: str, label: str | None
) -> InternalDomainModel:
    """Create a new internal domain."""
    entry = InternalDomainModel(id=domain_id, domain=domain, label=label)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_internal_domains(db: AsyncSession) -> list[InternalDomainModel]:
    """List all internal domains ordered by creation date."""
    result = await db.execute(
        select(InternalDomainModel).order_by(InternalDomainModel.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_internal_domain(db: AsyncSession, domain_id: str) -> bool:
    """Delete an internal domain. Returns True if deleted, False if not found."""
    result = await db.execute(
        select(InternalDomainModel).where(InternalDomainModel.id == domain_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return False
    await db.delete(entry)
    await db.commit()
    return True
```

- [ ] **Step 3: Commit**

```bash
git add apps/middleware-api/app/db/models.py apps/middleware-api/app/db/repository.py
git commit -m "feat: DLP database models and repository CRUD functions"
```

---

### Task 5: DLP Pydantic Schemas

**Files:**
- Create: `apps/middleware-api/app/schemas/dlp.py`

- [ ] **Step 1: Create DLP Pydantic schemas**

Create `apps/middleware-api/app/schemas/dlp.py`:

```python
"""Pydantic schemas for DLP management endpoints."""

from datetime import datetime

from pydantic import BaseModel, IPvAnyNetwork, field_validator


class InternalNetworkCreate(BaseModel):
    """Request schema for creating an internal network CIDR block."""

    cidr: IPvAnyNetwork
    label: str | None = None


class InternalNetworkResponse(BaseModel):
    """Response schema for an internal network entry."""

    id: str
    cidr: str
    label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InternalDomainCreate(BaseModel):
    """Request schema for creating an internal domain."""

    domain: str
    label: str | None = None

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        """Normalize domain to lowercase and strip whitespace."""
        return v.strip().lower()


class InternalDomainResponse(BaseModel):
    """Response schema for an internal domain entry."""

    id: str
    domain: str
    label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
git add apps/middleware-api/app/schemas/dlp.py
git commit -m "feat: Pydantic schemas for DLP management endpoints"
```

---

### Task 6: DLP Router Endpoints (TDD)

**Files:**
- Create: `apps/middleware-api/tests/test_dlp_routes.py`
- Create: `apps/middleware-api/app/router/dlp.py`

- [ ] **Step 1: Write failing integration tests for DLP routes**

Create `apps/middleware-api/tests/test_dlp_routes.py`:

```python
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
        # Create a network first
        await client.post(
            "/api/dlp/networks",
            json={"cidr": "172.16.0.0/12"},
        )
        response = await client.get("/api/dlp/networks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    async def test_delete_network(self, client: AsyncClient) -> None:
        # Create, then delete
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
        assert data["domain"] == "company.com"  # normalized to lowercase
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/middleware-api && python -m pytest tests/test_dlp_routes.py -v`
Expected: FAIL — routes not registered

- [ ] **Step 3: Implement DLP router**

Create `apps/middleware-api/app/router/dlp.py`:

```python
"""FastAPI router for DLP management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.db.connection import get_db
from app.db import repository
from app.schemas.dlp import (
    InternalDomainCreate,
    InternalDomainResponse,
    InternalNetworkCreate,
    InternalNetworkResponse,
)
from app.services.dlp_classifier import dlp_classifier

router = APIRouter(prefix="/api/dlp", tags=["dlp"])


# --- Internal Networks ---


@router.post("/networks", response_model=InternalNetworkResponse, status_code=201)
async def create_network(
    body: InternalNetworkCreate,
    db: AsyncSession = Depends(get_db),
) -> InternalNetworkResponse:
    """Add an internal CIDR block to the DLP rules."""
    try:
        network = await repository.create_internal_network(
            db,
            network_id=str(ULID()),
            cidr=str(body.cidr),
            label=body.label,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="CIDR block already exists")
    return InternalNetworkResponse.model_validate(network)


@router.get("/networks", response_model=list[InternalNetworkResponse])
async def list_networks(
    db: AsyncSession = Depends(get_db),
) -> list[InternalNetworkResponse]:
    """List all internal network CIDR blocks."""
    networks = await repository.list_internal_networks(db)
    return [InternalNetworkResponse.model_validate(n) for n in networks]


@router.delete("/networks/{network_id}", status_code=204)
async def delete_network(
    network_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove an internal CIDR block."""
    deleted = await repository.delete_internal_network(db, network_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Network not found")
    return Response(status_code=204)


# --- Internal Domains ---


@router.post("/domains", response_model=InternalDomainResponse, status_code=201)
async def create_domain(
    body: InternalDomainCreate,
    db: AsyncSession = Depends(get_db),
) -> InternalDomainResponse:
    """Add an internal domain to the DLP rules."""
    try:
        entry = await repository.create_internal_domain(
            db,
            domain_id=str(ULID()),
            domain=body.domain,
            label=body.label,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Domain already exists")
    return InternalDomainResponse.model_validate(entry)


@router.get("/domains", response_model=list[InternalDomainResponse])
async def list_domains(
    db: AsyncSession = Depends(get_db),
) -> list[InternalDomainResponse]:
    """List all internal domains."""
    domains = await repository.list_internal_domains(db)
    return [InternalDomainResponse.model_validate(d) for d in domains]


@router.delete("/domains/{domain_id}", status_code=204)
async def delete_domain(
    domain_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove an internal domain."""
    deleted = await repository.delete_internal_domain(db, domain_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Domain not found")
    return Response(status_code=204)


# --- Cache Refresh ---


@router.post("/refresh", status_code=204)
async def refresh_cache(
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Force-reload the DLP classifier cache from the database."""
    await dlp_classifier.load(db)
    return Response(status_code=204)
```

- [ ] **Step 4: Register DLP router in `apps/middleware-api/app/main.py`**

Add the import (line 11, after existing router imports):

```python
from app.router import sessions, uploads, dlp
```

Add the router registration (after line 40):

```python
app.include_router(dlp.router)
```

- [ ] **Step 5: Run integration tests**

Run: `cd apps/middleware-api && python -m pytest tests/test_dlp_routes.py -v`
Expected: All tests PASS (requires running PostgreSQL with updated init.sql)

Note: If tests run against a DB with the old schema, the DB must be recreated: `docker compose down -v && docker compose up -d postgres-db`

- [ ] **Step 6: Commit**

```bash
git add apps/middleware-api/app/router/dlp.py apps/middleware-api/tests/test_dlp_routes.py apps/middleware-api/app/main.py
git commit -m "feat: DLP CRUD and refresh endpoints with integration tests"
```

---

### Task 7: Integrate DLP into Upload Flow + Load Cache at Startup

**Files:**
- Modify: `apps/middleware-api/app/router/uploads.py:3-4,17-21,46`
- Modify: `apps/middleware-api/app/main.py:14-17`

- [ ] **Step 1: Add DlpClassifier to upload endpoint in `apps/middleware-api/app/router/uploads.py`**

Add the import after line 4 (after existing imports):

```python
from app.services.dlp_classifier import DlpClassifier, get_dlp_classifier
```

Modify the `upload_file` function signature (lines 17-21) to add the DLP dependency:

```python
@router.post("/{session_id}/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    session_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    dlp: DlpClassifier = Depends(get_dlp_classifier),
) -> UploadResponse:
```

Add the classify call after IOC extraction (after line 46 `iocs = extract_iocs(text)`):

```python
    iocs = extract_iocs(text)
    iocs = dlp.classify(iocs)
```

- [ ] **Step 2: Load DLP cache at startup in `apps/middleware-api/app/main.py`**

Add the import:

```python
from app.services.dlp_classifier import dlp_classifier
from app.db.connection import async_session_factory
```

Update the lifespan function to load the DLP cache:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startet und beendet die Datenbankverbindung mit der App."""
    # Load DLP rules into memory at startup
    async with async_session_factory() as db:
        await dlp_classifier.load(db)
    yield
    # Datenbankverbindungen beim Herunterfahren schliessen
    await engine.dispose()
```

- [ ] **Step 3: Run full test suite**

Run: `cd apps/middleware-api && python -m pytest -v`
Expected: All tests PASS (including existing session, upload, health, IOC extractor tests)

- [ ] **Step 4: Commit**

```bash
git add apps/middleware-api/app/router/uploads.py apps/middleware-api/app/main.py
git commit -m "feat: integrate DLP classification into upload flow and startup"
```

---

### Task 8: End-to-End Verification

- [ ] **Step 1: Rebuild Docker containers with new schema**

Run:
```bash
docker compose down -v
docker compose up -d --build
```

Wait for all containers to be healthy.

- [ ] **Step 2: Seed DLP rules via API**

```bash
curl -X POST http://localhost:8000/api/dlp/networks \
  -H "Content-Type: application/json" \
  -d '{"cidr": "10.0.0.0/8", "label": "Private range"}'

curl -X POST http://localhost:8000/api/dlp/networks \
  -H "Content-Type: application/json" \
  -d '{"cidr": "192.168.0.0/16", "label": "LAN"}'

curl -X POST http://localhost:8000/api/dlp/domains \
  -H "Content-Type: application/json" \
  -d '{"domain": "company.com", "label": "Corporate"}'

curl -X POST http://localhost:8000/api/dlp/refresh
```

- [ ] **Step 3: Test upload with mixed IOCs**

Create a test file `test-iocs.txt` with:
```
Suspicious IP: 8.8.8.8
Internal server: 10.0.0.42
External domain: evil.com
Internal domain: api.company.com
Hash: 44d88612fea8a8f36de82e1278abb02f
```

Upload it:
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "DLP Test"}'
# Use the returned session ID:
curl -X POST http://localhost:8000/api/sessions/{SESSION_ID}/upload \
  -F "file=@test-iocs.txt"
```

Verify response: `10.0.0.42` and `api.company.com` should have `status: "INTERNAL"`, others should be `"PENDING"`.

- [ ] **Step 4: Verify in browser**

Open `http://localhost:3000`, navigate to the session. INTERNAL assets should show a red badge (not a dropdown).

- [ ] **Step 5: Clean up test file**

```bash
rm test-iocs.txt
```

- [ ] **Step 6: Final commit if any adjustments were needed**

```bash
git add -A
git commit -m "fix: adjustments from E2E verification"
```
