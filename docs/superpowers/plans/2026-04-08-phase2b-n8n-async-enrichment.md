# Phase 2B: n8n Async Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build the async enrichment pipeline: analyst selects assets, FastAPI dispatches to n8n, n8n calls back with threat intel, frontend polls for updates.

**Architecture:** FastAPI enrich endpoint marks assets PROCESSING and fires BackgroundTask to n8n webhook. n8n fans out to VirusTotal/AbuseIPDB, calls back with results. Callback endpoint updates assets with idempotency guard. Frontend polls while PROCESSING assets exist.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, httpx, Pydantic v2, PostgreSQL JSONB/ARRAY, React, Zustand, TanStack Table, n8n, Docker Compose

---

## File Structure

### New Files
- apps/middleware-api/app/schemas/enrichment.py - Pydantic schemas for enrich/callback
- apps/middleware-api/app/router/enrichment.py - POST /api/sessions/{id}/enrich
- apps/middleware-api/app/router/callbacks.py - POST /api/callbacks/n8n
- apps/middleware-api/app/services/n8n_dispatcher.py - Background task to POST to n8n
- apps/middleware-api/tests/test_enrichment_endpoint.py - Enrich endpoint tests
- apps/middleware-api/tests/test_callback_endpoint.py - Callback endpoint tests
- apps/middleware-api/tests/test_n8n_dispatcher.py - Dispatcher unit tests
- infrastructure/n8n/workflows/README.md - n8n CLI instructions
- .env.example - API key documentation

### Modified Files
- infrastructure/db/init.sql - enrichment_data column + enrichment_batches table
- apps/middleware-api/app/db/models.py - EnrichmentBatchModel + enrichment_data column
- apps/middleware-api/app/db/repository.py - Batch CRUD + bulk asset updates
- apps/middleware-api/app/core/config.py - n8n_webhook_url + middleware_internal_url
- apps/middleware-api/app/main.py - Register routers + httpx lifecycle
- apps/middleware-api/app/router/sessions.py - GET /api/sessions/{id} endpoint
- apps/middleware-api/app/schemas/asset.py - Add enrichment_data to AssetResponse
- apps/middleware-api/requirements.txt - No changes needed (httpx already present)
- docker-compose.yml - n8n service + env vars + volume
- apps/web-ui/src/types/index.ts - enrichment_data on AnalyzedAsset
- apps/web-ui/src/api/apiClient.ts - enrichAssets() + getSession()
- apps/web-ui/src/store/sessionStore.ts - markAssetsProcessing + refreshSessionAssets
- apps/web-ui/src/components/AssetTable.tsx - Row selection + enrich button + badges

---

### Task 1: Database Schema + SQLAlchemy Models

**Files:**
- Modify: infrastructure/db/init.sql
- Modify: apps/middleware-api/app/db/models.py

- [ ] **Step 1: Add enrichment_data column and enrichment_batches table to init.sql**

Add at the end of infrastructure/db/init.sql:

```sql
-- Phase 2B: Enrichment data storage
ALTER TABLE assets ADD COLUMN enrichment_data JSONB DEFAULT '"'"'{}'"'"'::jsonb;

-- Phase 2B: Batch tracking for n8n dispatch
CREATE TABLE enrichment_batches (
    id            CHAR(26) PRIMARY KEY,
    session_id    CHAR(26) REFERENCES sessions(id) ON DELETE CASCADE,
    asset_ids     CHAR(26)[] NOT NULL,
    status        VARCHAR(20) DEFAULT '"'"'DISPATCHED'"'"'
                  CHECK (status IN ('"'"'DISPATCHED'"'"', '"'"'COMPLETED'"'"', '"'"'PARTIAL'"'"', '"'"'FAILED'"'"')),
    dispatched_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);
```

- [ ] **Step 2: Add enrichment_data to AssetModel in models.py**

In apps/middleware-api/app/db/models.py, add import and column:

Add to imports: from sqlalchemy import text (already has DateTime, Enum, etc.)
Add to imports: from sqlalchemy.dialects.postgresql import JSONB (alongside existing CIDR import)

Add column to AssetModel after the created_at column:

```python
enrichment_data: Mapped[dict] = mapped_column(
    JSONB, server_default=text("'"'"'{}'"'"'::jsonb"), nullable=False
)
```

- [ ] **Step 3: Add EnrichmentBatchModel to models.py**

Add to imports: from sqlalchemy.dialects.postgresql import ARRAY (same line as CIDR, JSONB)

Add new model class after InternalDomainModel:

```python
class EnrichmentBatchModel(Base):
    """Database table for enrichment batch tracking."""

    __tablename__ = "enrichment_batches"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    asset_ids: Mapped[list[str]] = mapped_column(ARRAY(String(26)), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), server_default="DISPATCHED", nullable=False
    )
    dispatched_at: Mapped[DateTime] = mapped_column(
        "dispatched_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[DateTime | None] = mapped_column(
        "completed_at",
        DateTime(timezone=True),
        nullable=True,
    )
```

- [ ] **Step 4: Rebuild Docker containers to apply schema**

Run: docker compose down && docker compose up -d --build
Note: init.sql only runs on fresh DB. If pg_data volume exists, drop it first: docker volume rm seccenter_pg_data

- [ ] **Step 5: Commit**

```bash
git add -f infrastructure/db/init.sql apps/middleware-api/app/db/models.py
git commit -m "feat: add enrichment_data column and enrichment_batches table"
```

### Task 2: Pydantic Schemas + Config + AssetResponse Update

**Files:**
- Create: apps/middleware-api/app/schemas/enrichment.py
- Modify: apps/middleware-api/app/core/config.py
- Modify: apps/middleware-api/app/schemas/asset.py

- [ ] **Step 1: Create enrichment schemas**

Create apps/middleware-api/app/schemas/enrichment.py:

```python
"""Pydantic schemas for enrichment dispatch and n8n callback."""

from typing import Any, Literal

from pydantic import BaseModel


class EnrichRequest(BaseModel):
    """Request body for POST /api/sessions/{id}/enrich."""
    asset_ids: list[str]


class EnrichResponse(BaseModel):
    """Response for successful enrichment dispatch."""
    batch_id: str
    asset_count: int


class EnrichmentResult(BaseModel):
    """Single asset result from n8n callback."""
    asset_id: str
    status: Literal["ENRICHED", "CRITICAL"]
    threat_intel: dict[str, Any]


class N8nCallbackRequest(BaseModel):
    """Request body from n8n callback POST /api/callbacks/n8n."""
    session_id: str
    batch_id: str
    results: list[EnrichmentResult]


class N8nCallbackResponse(BaseModel):
    """Response after processing n8n callback."""
    batch_id: str
    updated: int
```

- [ ] **Step 2: Add n8n settings to config.py**

In apps/middleware-api/app/core/config.py, add two fields to Settings class after max_upload_bytes:

```python
# n8n webhook URL for enrichment dispatch
n8n_webhook_url: str = "http://n8n-orchestrator:5678/webhook/enrich"

# Internal URL of this middleware (for callback_url in n8n payload)
middleware_internal_url: str = "http://middleware-api:8000"
```

- [ ] **Step 3: Add enrichment_data to AssetResponse**

In apps/middleware-api/app/schemas/asset.py, add to AssetResponse class after created_at:

```python
enrichment_data: dict = {}
```

This ensures the API returns enrichment_data for polling. Default {} matches the DB default.

- [ ] **Step 4: Commit**

```bash
git add apps/middleware-api/app/schemas/enrichment.py apps/middleware-api/app/core/config.py apps/middleware-api/app/schemas/asset.py
git commit -m "feat: add enrichment schemas, config, and AssetResponse update"
```

### Task 3: Repository Functions for Batches and Bulk Updates

**Files:**
- Modify: apps/middleware-api/app/db/repository.py

- [ ] **Step 1: Add batch and enrichment repository functions**

Add imports at top of apps/middleware-api/app/db/repository.py:

```python
from datetime import datetime, timezone
from app.db.models import EnrichmentBatchModel
```

Add these functions after the existing delete_internal_domain function:

```python
async def create_enrichment_batch(
    db: AsyncSession, batch_id: str, session_id: str, asset_ids: list[str]
) -> EnrichmentBatchModel:
    """Create a new enrichment batch record."""
    batch = EnrichmentBatchModel(
        id=batch_id, session_id=session_id, asset_ids=asset_ids
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


async def get_enrichment_batch(
    db: AsyncSession, batch_id: str
) -> EnrichmentBatchModel | None:
    """Get an enrichment batch by ID."""
    result = await db.execute(
        select(EnrichmentBatchModel).where(EnrichmentBatchModel.id == batch_id)
    )
    return result.scalar_one_or_none()


async def update_batch_status(
    db: AsyncSession, batch_id: str, status: str
) -> None:
    """Update batch status and set completed_at if terminal."""
    result = await db.execute(
        select(EnrichmentBatchModel).where(EnrichmentBatchModel.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if batch:
        batch.status = status
        if status in ("COMPLETED", "PARTIAL", "FAILED"):
            batch.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def bulk_mark_assets_processing(
    db: AsyncSession, asset_ids: list[str]
) -> None:
    """Mark multiple assets as PROCESSING in one transaction."""
    for asset_id in asset_ids:
        result = await db.execute(
            select(AssetModel).where(AssetModel.id == asset_id)
        )
        asset = result.scalar_one_or_none()
        if asset:
            asset.status = "PROCESSING"
    await db.commit()


async def bulk_revert_assets_to_pending(
    db: AsyncSession, asset_ids: list[str]
) -> None:
    """Revert assets from PROCESSING back to PENDING (compensating transaction)."""
    for asset_id in asset_ids:
        result = await db.execute(
            select(AssetModel).where(
                AssetModel.id == asset_id,
            )
        )
        asset = result.scalar_one_or_none()
        if asset and asset.status == "PROCESSING":
            asset.status = "PENDING"
    await db.commit()


async def update_asset_enrichment(
    db: AsyncSession, asset_id: str, status: str, enrichment_data: dict
) -> bool:
    """Update asset status and enrichment data. Only updates if currently PROCESSING."""
    result = await db.execute(
        select(AssetModel).where(
            AssetModel.id == asset_id,
        )
    )
    asset = result.scalar_one_or_none()
    if asset and asset.status == "PROCESSING":
        asset.status = status
        asset.enrichment_data = enrichment_data
        return True
    return False


async def get_assets_by_ids(
    db: AsyncSession, session_id: str, asset_ids: list[str]
) -> list[AssetModel]:
    """Get assets by IDs within a session."""
    result = await db.execute(
        select(AssetModel).where(
            AssetModel.session_id == session_id,
            AssetModel.id.in_(asset_ids),
        )
    )
    return list(result.scalars().all())
```

- [ ] **Step 2: Commit**

```bash
git add apps/middleware-api/app/db/repository.py
git commit -m "feat: add batch CRUD and bulk asset update repository functions"
```

### Task 4: n8n Dispatcher Service (with tests)

**Files:**
- Create: apps/middleware-api/app/services/n8n_dispatcher.py
- Create: apps/middleware-api/tests/test_n8n_dispatcher.py

- [ ] **Step 1: Write failing tests for dispatcher**

Create apps/middleware-api/tests/test_n8n_dispatcher.py:

```python
"""Unit tests for n8n dispatcher background task."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.n8n_dispatcher import dispatch_to_n8n


pytestmark = pytest.mark.asyncio


class TestDispatchToN8n:
    """Tests for the dispatch_to_n8n background task."""

    async def test_successful_dispatch(self) -> None:
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(status_code=200)
        mock_db_factory = AsyncMock()

        await dispatch_to_n8n(
            http_client=mock_client,
            webhook_url="http://n8n:5678/webhook/enrich",
            payload={"session_id": "s1", "batch_id": "b1", "assets": []},
            batch_id="b1",
            asset_ids=["a1"],
            db_session_factory=mock_db_factory,
        )

        mock_client.post.assert_called_once()

    async def test_failed_dispatch_triggers_compensating_transaction(self) -> None:
        import httpx
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        mock_session = AsyncMock()
        mock_db_factory = AsyncMock()
        mock_db_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.n8n_dispatcher.repository") as mock_repo:
            await dispatch_to_n8n(
                http_client=mock_client,
                webhook_url="http://n8n:5678/webhook/enrich",
                payload={"session_id": "s1", "batch_id": "b1", "assets": []},
                batch_id="b1",
                asset_ids=["a1", "a2"],
                db_session_factory=mock_db_factory,
            )

            mock_repo.update_batch_status.assert_called_once_with(
                mock_session, "b1", "FAILED"
            )
            mock_repo.bulk_revert_assets_to_pending.assert_called_once_with(
                mock_session, ["a1", "a2"]
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: docker compose exec middleware-api python -m pytest tests/test_n8n_dispatcher.py -v
Expected: FAIL (module not found)

- [ ] **Step 3: Implement dispatcher**

Create apps/middleware-api/app/services/n8n_dispatcher.py:

```python
"""Background task for dispatching enrichment batches to n8n."""

import logging

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import repository

logger = logging.getLogger(__name__)


async def dispatch_to_n8n(
    http_client: httpx.AsyncClient,
    webhook_url: str,
    payload: dict,
    batch_id: str,
    asset_ids: list[str],
    db_session_factory: async_sessionmaker,
) -> None:
    """POST hydrated payload to n8n webhook. On failure, run compensating transaction."""
    try:
        response = await http_client.post(webhook_url, json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info("Batch %s dispatched to n8n (status %d)", batch_id, response.status_code)
    except (httpx.HTTPError, httpx.ConnectError) as exc:
        logger.error("Batch %s dispatch failed: %s", batch_id, exc)
        async with db_session_factory() as db:
            await repository.update_batch_status(db, batch_id, "FAILED")
            await repository.bulk_revert_assets_to_pending(db, asset_ids)
        logger.info("Batch %s compensating transaction complete", batch_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: docker compose exec middleware-api python -m pytest tests/test_n8n_dispatcher.py -v
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add apps/middleware-api/app/services/n8n_dispatcher.py apps/middleware-api/tests/test_n8n_dispatcher.py
git commit -m "feat: add n8n dispatcher background task with compensating transaction"
```

### Task 5: Enrichment Endpoint + httpx Lifecycle (with tests)

**Files:**
- Create: apps/middleware-api/app/router/enrichment.py
- Create: apps/middleware-api/tests/test_enrichment_endpoint.py
- Modify: apps/middleware-api/app/main.py

- [ ] **Step 1: Write failing integration tests**

Create apps/middleware-api/tests/test_enrichment_endpoint.py with tests:
- test_enrich_returns_202: Create session + upload file, POST /enrich with asset_ids, assert 202 + batch_id + asset_count
- test_enrich_nonexistent_session_returns_404: POST to fake session_id, assert 404
- test_enrich_filters_internal_assets: Add DLP rule, upload mixed IOCs, enrich all IDs, assert asset_count only includes PENDING
- test_enrich_all_internal_returns_422: All assets internal, enrich returns 422

Helper method _create_session_with_assets: POST /sessions, POST /upload with "8.8.8.8 and evil.com", return (session_id, asset_ids).

- [ ] **Step 2: Run tests to verify they fail**

Run: docker compose exec middleware-api python -m pytest tests/test_enrichment_endpoint.py -v
Expected: FAIL (no endpoint)

- [ ] **Step 3: Implement enrichment router**

Create apps/middleware-api/app/router/enrichment.py:

Router with prefix /api/sessions, tag enrichment. Single endpoint:

POST /{session_id}/enrich (status_code=202, response_model=EnrichResponse):
1. Validate session (404)
2. get_assets_by_ids, filter to status in (PENDING, CONFIRMED) -> enrichable
3. If not enrichable: 422
4. Create batch with ULID
5. bulk_mark_assets_processing
6. Add background_tasks.add_task(dispatch_to_n8n, ...) with hydrated payload including callback_url from settings
7. Return EnrichResponse(batch_id, asset_count)

Import http_client from app.main (module-level global).

- [ ] **Step 4: Register router and add httpx client in main.py**

Add to imports: from app.router import enrichment; import httpx

Add module-level: http_client: httpx.AsyncClient (initialized as None, type-ignored)

In lifespan, after DLP load: http_client = httpx.AsyncClient()
In lifespan yield cleanup: await http_client.aclose() before engine.dispose()

Register: app.include_router(enrichment.router)

- [ ] **Step 5: Run tests to verify they pass**

Run: docker compose exec middleware-api python -m pytest tests/test_enrichment_endpoint.py -v
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add apps/middleware-api/app/router/enrichment.py apps/middleware-api/tests/test_enrichment_endpoint.py apps/middleware-api/app/main.py
git commit -m "feat: add POST /api/sessions/{id}/enrich endpoint with background dispatch"
```

### Task 6: Callback Endpoint (with tests)

**Files:**
- Create: apps/middleware-api/app/router/callbacks.py
- Create: apps/middleware-api/tests/test_callback_endpoint.py
- Modify: apps/middleware-api/app/main.py

- [ ] **Step 1: Write failing integration tests**

Create apps/middleware-api/tests/test_callback_endpoint.py with tests:
- test_callback_updates_assets: Create session, upload, enrich, then POST callback with ENRICHED results. Assert 200, assets updated.
- test_callback_idempotency: POST same callback twice. Second returns 200 without error.
- test_callback_nonexistent_batch_returns_404: POST callback with fake batch_id.
- test_callback_processing_guard: Manually change an asset to CONFIRMED before callback. Assert callback does not overwrite it.
- test_callback_partial_batch: Send results for only some assets. Assert batch status = PARTIAL.
- test_callback_all_errors_marks_failed: All results have threat_intel.error. Assert batch status = FAILED.

Each test creates session -> uploads file -> dispatches enrichment (to get a real batch_id), then calls the callback endpoint directly.

- [ ] **Step 2: Run tests to verify they fail**

Run: docker compose exec middleware-api python -m pytest tests/test_callback_endpoint.py -v
Expected: FAIL (no endpoint)

- [ ] **Step 3: Implement callback router**

Create apps/middleware-api/app/router/callbacks.py:

Router with prefix /api/callbacks, tag callbacks. Single endpoint:

POST /n8n (response_model=N8nCallbackResponse):
1. get_enrichment_batch by batch_id. 404 if not found.
2. If batch.status == "COMPLETED": return N8nCallbackResponse(batch_id, updated=0) immediately
3. Validate each result asset_id is in batch.asset_ids. Skip unknown IDs with log warning.
4. Loop through valid results: call repository.update_asset_enrichment(db, asset_id, status, threat_intel). Count successes.
5. Determine batch outcome:
   - len(results) == len(batch.asset_ids) and all succeeded -> COMPLETED
   - len(results) < len(batch.asset_ids) -> PARTIAL
   - all results have "error" key in threat_intel -> FAILED
   - else -> COMPLETED
6. update_batch_status
7. db.commit()
8. Return N8nCallbackResponse(batch_id, updated=count)

- [ ] **Step 4: Register callback router in main.py**

Add import: from app.router import callbacks
Add: app.include_router(callbacks.router)

- [ ] **Step 5: Run tests to verify they pass**

Run: docker compose exec middleware-api python -m pytest tests/test_callback_endpoint.py -v
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add apps/middleware-api/app/router/callbacks.py apps/middleware-api/tests/test_callback_endpoint.py apps/middleware-api/app/main.py
git commit -m "feat: add POST /api/callbacks/n8n endpoint with idempotency and PROCESSING guard"
```

### Task 7: GET /api/sessions/{id} Endpoint (for frontend polling)

**Files:**
- Modify: apps/middleware-api/app/router/sessions.py
- Modify: apps/middleware-api/app/schemas/session.py

- [ ] **Step 1: Update SessionResponse to include assets**

In apps/middleware-api/app/schemas/session.py, add import and field:

```python
from app.schemas.asset import AssetResponse

class SessionWithAssetsResponse(BaseModel):
    id: str
    name: str
    assets: list[AssetResponse] = []
    created_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Add GET endpoint to sessions router**

In apps/middleware-api/app/router/sessions.py, add after list_sessions:

```python
from app.schemas.session import SessionWithAssetsResponse

@router.get("/{session_id}", response_model=SessionWithAssetsResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionWithAssetsResponse:
    session = await repository.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionWithAssetsResponse.model_validate(session)
```

Note: The existing repository.get_session already loads the session. SQLAlchemy lazy-loads the assets relationship. If needed, add selectinload for eager loading.

- [ ] **Step 3: Test manually**

Run: docker compose exec middleware-api python -m pytest tests/test_sessions.py -v
Then test via curl: curl http://localhost:8000/api/sessions

- [ ] **Step 4: Commit**

```bash
git add apps/middleware-api/app/router/sessions.py apps/middleware-api/app/schemas/session.py
git commit -m "feat: add GET /api/sessions/{id} endpoint for frontend polling"
```

### Task 8: Docker Infrastructure (n8n container + env vars)

**Files:**
- Modify: docker-compose.yml
- Create: .env.example
- Create: infrastructure/n8n/workflows/README.md

- [ ] **Step 1: Add n8n service to docker-compose.yml**

Add n8n-orchestrator service after web-ui:

```yaml
  # n8n Workflow Orchestrator
  n8n-orchestrator:
    image: n8nio/n8n:1.94.1
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://n8n-orchestrator:5678/
      - N8N_USER_FOLDER=/home/node/.n8n
      - VT_API_KEY=${VT_API_KEY:-}
      - ABUSEIPDB_API_KEY=${ABUSEIPDB_API_KEY:-}
    volumes:
      - n8n_data:/home/node/.n8n
      - ./infrastructure/n8n/workflows:/home/node/.n8n/workflows
    depends_on:
      - middleware-api
    networks:
      - cockpit-net
```

Add n8n_data to volumes section:
```yaml
volumes:
  pg_data:
  n8n_data:
```

Add new env vars to middleware-api service:
```yaml
    environment:
      # ... existing ...
      - SECCENTER_N8N_WEBHOOK_URL=http://n8n-orchestrator:5678/webhook/enrich
      - SECCENTER_MIDDLEWARE_INTERNAL_URL=http://middleware-api:8000
```

- [ ] **Step 2: Create .env.example**

Create .env.example in project root:

```env
# n8n Enrichment API Keys (optional - n8n starts without them)
VT_API_KEY=
ABUSEIPDB_API_KEY=
```

- [ ] **Step 3: Create n8n workflows README**

Create directory: mkdir -p infrastructure/n8n/workflows

Create infrastructure/n8n/workflows/README.md with:
- Purpose: Version-controlled n8n workflow storage
- Export command: docker exec n8n-orchestrator n8n export:workflow --backup --output=/home/node/.n8n/workflows/
- Import command: docker exec n8n-orchestrator n8n import:workflow --input=/home/node/.n8n/workflows/
- Linux permission note: chown -R 1000:1000 ./infrastructure/n8n/workflows if EACCES

- [ ] **Step 4: Verify docker-compose up works**

Run: docker compose down && docker compose up -d
Verify: n8n accessible at http://localhost:5678, middleware still healthy at http://localhost:8000/api/health

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example
git add -f infrastructure/n8n/workflows/README.md
git commit -m "feat: add n8n orchestrator container and enrichment infrastructure"
```

### Task 9: Frontend - Types + API Client

**Files:**
- Modify: apps/web-ui/src/types/index.ts
- Modify: apps/web-ui/src/api/apiClient.ts

- [ ] **Step 1: Add enrichment_data to AnalyzedAsset type**

In apps/web-ui/src/types/index.ts, add to AnalyzedAsset interface after created_at:

```typescript
enrichment_data: Record<string, unknown>;
```

- [ ] **Step 2: Add enrichAssets and getSession to API client**

In apps/web-ui/src/api/apiClient.ts, add two new functions before the apiClient object:

```typescript
/**
 * Dispatches selected assets for enrichment via n8n
 */
export async function enrichAssets(
  sessionId: string,
  assetIds: string[]
): Promise<{ batch_id: string; asset_count: number }> {
  return fetchJson<{ batch_id: string; asset_count: number }>(
    `/sessions/${sessionId}/enrich`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_ids: assetIds }),
    }
  );
}

/**
 * Fetches a single session with all its assets (used for polling)
 */
export async function getSession(
  sessionId: string
): Promise<AnalysisSession> {
  return fetchJson<AnalysisSession>(`/sessions/${sessionId}`);
}
```

Add both to the apiClient object:
```typescript
export const apiClient = {
  createSession,
  listSessions,
  uploadFile,
  updateAssetStatus,
  enrichAssets,
  getSession,
};
```

- [ ] **Step 3: Commit**

```bash
git add apps/web-ui/src/types/index.ts apps/web-ui/src/api/apiClient.ts
git commit -m "feat: add enrichment types and API client methods"
```

### Task 10: Frontend - Zustand Store Extensions

**Files:**
- Modify: apps/web-ui/src/store/sessionStore.ts

- [ ] **Step 1: Add new actions to SessionState interface**

In apps/web-ui/src/store/sessionStore.ts, add to the SessionState interface:

```typescript
/** Mark assets as PROCESSING after successful enrich dispatch */
markAssetsProcessing: (sessionId: string, assetIds: string[]) => void;
/** Replace all assets for a session (polling sync from backend) */
refreshSessionAssets: (sessionId: string, assets: AnalyzedAsset[]) => void;
```

- [ ] **Step 2: Implement the actions in the store**

Add after the updateAssetStatus implementation:

```typescript
markAssetsProcessing: (sessionId, assetIds) =>
  set((state) => {
    const session = state.sessions[sessionId];
    if (session) {
      for (const asset of session.assets) {
        if (assetIds.includes(asset.id)) {
          asset.status = "PROCESSING";
        }
      }
    }
  }),

refreshSessionAssets: (sessionId, assets) =>
  set((state) => {
    const session = state.sessions[sessionId];
    if (session) {
      session.assets = assets;
    }
  }),
```

- [ ] **Step 3: Commit**

```bash
git add apps/web-ui/src/store/sessionStore.ts
git commit -m "feat: add markAssetsProcessing and refreshSessionAssets store actions"
```

### Task 11: Frontend - AssetTable (Row Selection, Enrich Button, Status Badges, Polling)

**Files:**
- Modify: apps/web-ui/src/components/AssetTable.tsx

This is the largest frontend task. It modifies AssetTable to add:
1. Checkbox column for row selection
2. "Enrich Selected" button above the table
3. Updated status badges (PROCESSING: blue+spinner, ENRICHED: green, CRITICAL: amber)
4. Polling via useEffect

- [ ] **Step 1: Add row selection to TanStack Table**

Import RowSelectionState from @tanstack/react-table.

Add state: const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

Add to useReactTable config:
```typescript
state: { sorting, rowSelection },
onRowSelectionChange: setRowSelection,
enableRowSelection: (row) =>
  row.original.status === "PENDING" || row.original.status === "CONFIRMED",
```

Add checkbox column as first column:

```typescript
columnHelper.display({
  id: "select",
  header: ({ table }) => (
    <input
      type="checkbox"
      checked={table.getIsAllPageRowsSelected()}
      onChange={table.getToggleAllPageRowsSelectedHandler()}
    />
  ),
  cell: ({ row }) => (
    <input
      type="checkbox"
      checked={row.getIsSelected()}
      disabled={!row.getCanSelect()}
      onChange={row.getToggleSelectedHandler()}
    />
  ),
}),
```

- [ ] **Step 2: Add "Enrich Selected" button**

Above the Table component, add:

```typescript
const selectedAssetIds = table
  .getSelectedRowModel()
  .rows.map((row) => row.original.id);

async function handleEnrich() {
  if (!activeSessionId || selectedAssetIds.length === 0) return;
  try {
    await apiClient.enrichAssets(activeSessionId, selectedAssetIds);
    markAssetsProcessing(activeSessionId, selectedAssetIds);
    setRowSelection({});
  } catch (error: unknown) {
    console.error("Enrichment dispatch failed:", error);
  }
}
```

Add markAssetsProcessing to the useSessionStore selector.
Add apiClient import.

Render button:
```tsx
<div className="mb-2 flex items-center gap-2">
  <Button
    size="sm"
    onClick={() => void handleEnrich()}
    disabled={selectedAssetIds.length === 0}
  >
    Enrich Selected ({selectedAssetIds.length})
  </Button>
</div>
```

- [ ] **Step 3: Update status badges**

In the status column cell renderer, update the non-editable statuses section to include visual distinctions:

PROCESSING: blue background with a small spinner (use animate-spin on an SVG or just text "PROCESSING..." with blue styling)
```tsx
if (asset.status === "PROCESSING") {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-blue-700 border-t-transparent" />
      PROCESSING
    </span>
  );
}
```

ENRICHED: green badge
```tsx
if (asset.status === "ENRICHED") {
  return (
    <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-700">
      ENRICHED
    </span>
  );
}
```

CRITICAL: amber badge
```tsx
if (asset.status === "CRITICAL") {
  return (
    <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-700">
      CRITICAL
    </span>
  );
}
```

Update the non-editable check to only cover statuses not handled above:
Remove PROCESSING, ENRICHED, CRITICAL from the generic non-editable block (they now have their own renderers).

- [ ] **Step 4: Add polling via useEffect**

Add after the store selectors:

```typescript
import { useEffect } from "react";  // add to existing import

const hasProcessingAssets = assets.some((a) => a.status === "PROCESSING");

useEffect(() => {
  if (!hasProcessingAssets || !activeSessionId) return;

  const intervalId = setInterval(async () => {
    try {
      const session = await apiClient.getSession(activeSessionId);
      useSessionStore.getState().refreshSessionAssets(activeSessionId, session.assets);
    } catch (error: unknown) {
      console.error("Polling failed:", error);
    }
  }, 5000);

  return () => clearInterval(intervalId);
}, [hasProcessingAssets, activeSessionId]);
```

- [ ] **Step 5: Verify in browser**

Run: docker compose up -d --build
Open: http://localhost:3000
Test: Create session, upload file, verify checkboxes appear on PENDING rows, "Enrich Selected" button works (will get 502 since n8n workflow not configured yet, but UI should handle gracefully).

- [ ] **Step 6: Commit**

```bash
git add apps/web-ui/src/components/AssetTable.tsx
git commit -m "feat: add row selection, enrich button, status badges, and polling to AssetTable"
```

### Task 12: End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: docker compose exec middleware-api python -m pytest -v
Expected: All tests pass (existing + new enrichment/callback/dispatcher tests)

- [ ] **Step 2: E2E test via curl**

```bash
# Create session
curl -s -X POST http://localhost:8000/api/sessions -H "Content-Type: application/json" -d '{"name":"E2E Test"}' | python -m json.tool

# Upload file (use the session_id from above)
curl -s -X POST http://localhost:8000/api/sessions/{SESSION_ID}/upload -F "file=@-;filename=test.txt;type=text/plain" <<< "IOCs: 8.8.8.8 and evil.com"

# Enrich (use asset_ids from upload response)
curl -s -X POST http://localhost:8000/api/sessions/{SESSION_ID}/enrich -H "Content-Type: application/json" -d '{"asset_ids":["ASSET_ID_1","ASSET_ID_2"]}'
# Expected: 202 with batch_id

# Simulate n8n callback (use batch_id from enrich response)
curl -s -X POST http://localhost:8000/api/callbacks/n8n -H "Content-Type: application/json" -d '{"session_id":"SESSION_ID","batch_id":"BATCH_ID","results":[{"asset_id":"ASSET_ID_1","status":"ENRICHED","threat_intel":{"vt_score":0}},{"asset_id":"ASSET_ID_2","status":"CRITICAL","threat_intel":{"vt_score":8}}]}'
# Expected: 200 with updated count

# Verify via GET session
curl -s http://localhost:8000/api/sessions/{SESSION_ID} | python -m json.tool
# Expected: assets show ENRICHED/CRITICAL status with enrichment_data populated
```

- [ ] **Step 3: Verify frontend**

Open http://localhost:3000. Create session, upload file, select assets, click "Enrich Selected". Verify:
- Assets show blue PROCESSING badges
- Polling is active (check Network tab for GET requests every 5s)
- After simulating callback via curl, assets update to ENRICHED (green) or CRITICAL (amber)

- [ ] **Step 4: Final commit with any fixes**

If any fixes were needed during E2E, commit them now.
