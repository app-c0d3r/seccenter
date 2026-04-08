# Phase 2A: DLP Foundation — Design Specification

## 1. Goal

Build the deterministic Data Leakage Prevention (DLP) layer that classifies extracted IOCs as `INTERNAL` or `PENDING` before they are persisted to the database. Internal assets are blocked from ever reaching external enrichment APIs (n8n/VirusTotal/AbuseIPDB). This is the non-negotiable security foundation for all subsequent Phase 2 work.

## 2. Architecture Decisions

All critical design decisions were explored and locked in during brainstorming:

| Decision | Choice | Rationale |
|---|---|---|
| Domain matching | Automatic suffix match | `company.com` matches all subdomains. Secure by default — no wildcard syntax, no human error |
| IP matching | In-memory Python `ipaddress` | Same caching strategy as domains. Zero DB roundtrips on hot path. Internal CIDR lists are small config data |
| Cache strategy | Explicit refresh endpoint | No TTL window where new rules are missed. No restart required. Admin calls `POST /api/dlp/refresh` after changes |
| Asset status enum | Full lifecycle upfront | `PENDING, INTERNAL, PROCESSING, ENRICHED, CRITICAL, CONFIRMED, IGNORED`. Avoids Postgres ENUM transaction quirk with Alembic later |
| CIDR storage | PostgreSQL native `CIDR` type | Validates on insert, no invalid ranges possible |
| Domain normalization | Lowercase on write and read | Enforced in Pydantic validator on create, and in classifier on lookup |

## 3. PostgreSQL Schema Changes

### 3.1 Extended Asset Status Enum

```sql
-- New asset lifecycle states (run outside transaction block)
ALTER TYPE asset_status ADD VALUE 'INTERNAL';
ALTER TYPE asset_status ADD VALUE 'PROCESSING';
ALTER TYPE asset_status ADD VALUE 'ENRICHED';
ALTER TYPE asset_status ADD VALUE 'CRITICAL';
```

Note: `ALTER TYPE ... ADD VALUE` cannot run inside a transaction block in PostgreSQL. In `init.sql` for Docker this is fine. Future Alembic migrations must use `execution_options={"autocommit": True}`.

### 3.2 Internal Networks Table

```sql
CREATE TABLE internal_networks (
    id          CHAR(26) PRIMARY KEY,
    cidr        CIDR NOT NULL,
    label       VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_internal_networks_cidr ON internal_networks(cidr);
```

### 3.3 Internal Domains Table

```sql
CREATE TABLE internal_domains (
    id          CHAR(26) PRIMARY KEY,
    domain      VARCHAR(255) NOT NULL,
    label       VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_internal_domains_domain ON internal_domains(domain);
```

Key properties:
- `CIDR` native type validates IP ranges on insert (rejects invalid input at DB level)
- `label` column for human-readable descriptions (future admin UI)
- Unique indexes prevent duplicate entries
- Domains are stored lowercase (enforced by Pydantic validator on write)

## 4. DlpClassifier Service

**File:** `apps/middleware-api/app/services/dlp_classifier.py`

### 4.1 DlpCache (Immutable Snapshot)

```python
import ipaddress
from dataclasses import dataclass, field

@dataclass
class DlpCache:
    """Immutable snapshot of DLP rules loaded from the database."""
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = field(default_factory=list)
    domains: set[str] = field(default_factory=set)  # all lowercase
```

An immutable dataclass enables lock-free, atomic reference swapping on refresh. Python GIL makes the assignment `self._cache = new_cache` thread-safe.

### 4.2 DlpClassifier

```python
class DlpClassifier:
    def __init__(self):
        self._cache = DlpCache()

    async def load(self, db: AsyncSession) -> None:
        """Load DLP rules from DB. Called at startup and on POST /api/dlp/refresh."""
        # Query internal_networks, parse each row cidr string to ip_network()
        # Query internal_domains (already lowercase in DB), collect into set
        # Atomic swap
        self._cache = DlpCache(networks=networks, domains=domains)

    def is_internal_ip(self, ip: str) -> bool:
        """Check if IP falls within any internal CIDR block."""
        try:
            addr = ipaddress.ip_address(ip)
            return any(addr in net for net in self._cache.networks)
        except ValueError:
            return False  # defense in depth: malformed IP cannot match

    def is_internal_domain(self, domain: str) -> bool:
        """Suffix match: api.staging.company.com matches company.com."""
        domain = domain.lower()
        parts = domain.split(".")
        for i in range(len(parts)):  # includes single-label domains
            candidate = ".".join(parts[i:])
            if candidate in self._cache.domains:
                return True
        return False

    def classify(self, iocs: list[dict]) -> list[dict]:
        """Tag each IOC with status based on DLP rules.
        IP_ADDRESS and DOMAIN types are checked. Hashes always get PENDING."""
        for ioc in iocs:
            if ioc["type"] == "IP_ADDRESS" and self.is_internal_ip(ioc["value"]):
                ioc["status"] = "INTERNAL"
            elif ioc["type"] == "DOMAIN" and self.is_internal_domain(ioc["value"]):
                ioc["status"] = "INTERNAL"
            else:
                ioc["status"] = "PENDING"
        return iocs
```

### 4.3 Design Properties

- **Pure classification**: `classify()` has no DB calls, no side effects — trivially testable via TDD
- **Defense in depth**: `is_internal_ip()` wraps parsing in try/except (never crashes on malformed input)
- **Single-label domains supported**: loop uses `range(len(parts))` not `range(len(parts) - 1)`
- **Hashes skip DLP**: file hashes have no concept of "internal" vs "external"
- **Belt and suspenders lowercase**: domains normalized on write (Pydantic) AND on read (classifier)

### 4.4 Singleton + FastAPI Integration

```python
# Module-level singleton
dlp_classifier = DlpClassifier()

# In main.py lifespan:
async def lifespan(app):
    async with async_session_factory() as db:
        await dlp_classifier.load(db)
    yield

# FastAPI dependency:
def get_dlp_classifier() -> DlpClassifier:
    return dlp_classifier
```

## 5. Upload Flow Integration

### 5.1 Modified Pipeline

```
BEFORE: Upload -> extract_iocs() -> repository.create_assets() -> Return
AFTER:  Upload -> extract_iocs() -> dlp_classifier.classify() -> repository.create_assets() -> Return
```

The change in `uploads.py` is surgical — add DLP dependency and one `classify()` call:

```python
@router.post("/{session_id}/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    session_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    dlp: DlpClassifier = Depends(get_dlp_classifier),
) -> UploadResponse:
    # ... existing session check and file read ...
    iocs = extract_iocs(text)
    iocs = dlp.classify(iocs)  # <-- NEW: tag INTERNAL before persistence
    # ... existing create_assets (status flows through via **asset_data) ...
```

The existing `repository.create_assets()` spreads `**asset_data` into `AssetModel()`, so the `status` key from `classify()` flows through automatically. No repository changes needed for the upload path.

## 6. API Endpoints

### 6.1 DLP Management Endpoints

| Method | Route | Purpose | Returns |
|---|---|---|---|
| `POST` | `/api/dlp/networks` | Add internal CIDR block | `InternalNetworkResponse` (201) |
| `GET` | `/api/dlp/networks` | List all internal networks | `InternalNetworkResponse[]` |
| `DELETE` | `/api/dlp/networks/{id}` | Remove a CIDR block | 204 No Content |
| `POST` | `/api/dlp/domains` | Add internal domain | `InternalDomainResponse` (201) |
| `GET` | `/api/dlp/domains` | List all internal domains | `InternalDomainResponse[]` |
| `DELETE` | `/api/dlp/domains/{id}` | Remove an internal domain | 204 No Content |
| `POST` | `/api/dlp/refresh` | Force-reload DLP cache from DB | 204 No Content |

### 6.2 Endpoint Behaviors

- **POST (create)**: Validates input via Pydantic. CIDR uses `IPvAnyNetwork` native type. Domain applies `.lower()` via `@field_validator`. Returns `409 Conflict` on duplicate (unique index violation).
- **DELETE**: Returns `204` on success, `404` if not found.
- **Refresh**: Idempotent. Re-queries both tables, builds new `DlpCache`, atomic swap. Does not auto-trigger on CRUD — admin batches changes, then refreshes once.

## 7. Pydantic Schemas

**File:** `apps/middleware-api/app/schemas/dlp.py`

```python
from pydantic import BaseModel, IPvAnyNetwork, field_validator
from datetime import datetime

class InternalNetworkCreate(BaseModel):
    cidr: IPvAnyNetwork  # Pydantic v2 native type — auto-validates
    label: str | None = None

class InternalNetworkResponse(BaseModel):
    id: str
    cidr: str
    label: str | None
    created_at: datetime
    model_config = {"from_attributes": True}

class InternalDomainCreate(BaseModel):
    domain: str
    label: str | None = None

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        return v.strip().lower()

class InternalDomainResponse(BaseModel):
    id: str
    domain: str
    label: str | None
    created_at: datetime
    model_config = {"from_attributes": True}
```

## 8. Updated Asset Status Enum

### 8.1 Full Lifecycle States

| Status | Meaning | Terminal? | Set by |
|---|---|---|---|
| `PENDING` | Awaiting enrichment pickup | No | DlpClassifier (default) |
| `INTERNAL` | Blocked by DLP rules | Yes | DlpClassifier |
| `PROCESSING` | Handed off to n8n | No | n8n webhook (Phase 2B) |
| `ENRICHED` | Returned clean from n8n | Yes | n8n callback (Phase 2B) |
| `CRITICAL` | Returned with threat indicators | Yes | n8n callback (Phase 2B) |
| `CONFIRMED` | Analyst manually confirmed | Yes | Analyst via UI |
| `IGNORED` | Analyst manually dismissed | Yes | Analyst via UI |

### 8.2 Files Updated

- `infrastructure/db/init.sql` — Add 4 new enum values to asset_status
- `apps/middleware-api/app/schemas/asset.py` — Python enum extended
- `apps/middleware-api/app/db/models.py` — SQLAlchemy enum extended
- `apps/web-ui/src/types/index.ts` — TypeScript union extended

## 9. File Change Summary

| File | Change |
|---|---|
| `infrastructure/db/init.sql` | Add enum values, `internal_networks` table, `internal_domains` table |
| `apps/middleware-api/app/services/dlp_classifier.py` | **New** — DlpClassifier, DlpCache, singleton |
| `apps/middleware-api/app/router/dlp.py` | **New** — CRUD + refresh endpoints |
| `apps/middleware-api/app/schemas/dlp.py` | **New** — Pydantic models for DLP entities |
| `apps/middleware-api/app/db/models.py` | Add InternalNetworkModel, InternalDomainModel, extend asset_status enum |
| `apps/middleware-api/app/db/repository.py` | Add DLP CRUD functions (create/list/delete for networks and domains) |
| `apps/middleware-api/app/router/uploads.py` | Add DlpClassifier dependency + `classify()` call (3 lines) |
| `apps/middleware-api/app/schemas/asset.py` | Extend AssetStatus enum with 4 new values |
| `apps/middleware-api/app/main.py` | Include DLP router, load DLP cache in lifespan |
| `apps/web-ui/src/types/index.ts` | Extend AssetStatus TypeScript union |
| `apps/middleware-api/tests/test_dlp_classifier.py` | **New** — Unit tests for classifier (TDD) |
| `apps/middleware-api/tests/test_dlp_routes.py` | **New** — Integration tests for DLP endpoints |

## 10. Phase 2A Scope Boundary

**In scope (this spec):**
- PostgreSQL schema for `internal_networks` and `internal_domains`
- Extended `asset_status` enum (full lifecycle)
- DlpClassifier service with in-memory cache
- DLP CRUD + refresh API endpoints
- Upload flow integration (classify before persist)
- Unit tests for classifier, integration tests for endpoints

**Explicitly out of scope:**
- n8n container and orchestration workflows (Phase 2B)
- Admin UI for managing DLP rules (Phase 4)
- Authentication/RBAC on DLP endpoints (Phase 4)
- Wildcard/exact match modes for domains (YAGNI)
- Automatic cache refresh via TTL (YAGNI)
