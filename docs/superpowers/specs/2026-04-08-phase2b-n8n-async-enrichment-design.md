# Phase 2B: n8n Async Enrichment — Design Specification

## 1. Goal

Build the asynchronous enrichment pipeline that dispatches PENDING assets to n8n for threat intelligence lookups (VirusTotal, AbuseIPDB), receives results via callback, and updates asset status and enrichment data in the database.

## 2. Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Enrichment trigger | Batch endpoint (POST /api/sessions/{id}/enrich) | Analyst controls enrichment. Preserves API quotas |
| Outbound payload | Hydrated JSON ({ id, value, type }) | n8n is stateless worker with no DB access |
| Inbound callback | Single batch POST (POST /api/callbacks/n8n) | n8n aggregates results, posts once |
| Failure handling | Timeout fallback (Option C) | n8n retries internally, sends whatever it has after timeout |
| Batch tracking | enrichment_batches table with batch_id | Idempotency, observability, retry support |
| CRITICAL threshold | Decided in n8n, not FastAPI | SOC admins tweak in n8n canvas without deploys |
| Polling vs WebSocket | Polling for Phase 2B | 5s poll. WebSocket deferred to Phase 3 |
| n8n credentials | Docker-compose env vars from .env | Matches existing pattern |
| n8n workflow IaC | Manual canvas build, JSON export to Git | Per CLAUDE.md |

## 3. Data Flow

Analyst clicks Enrich Selected -> POST /api/sessions/{id}/enrich -> FastAPI validates, filters enrichable, creates batch, marks PROCESSING, returns 202 -> BackgroundTask POSTs to n8n webhook -> n8n fans out to VirusTotal/AbuseIPDB with retries and timeout fallback -> n8n POSTs callback to /api/callbacks/n8n -> FastAPI checks idempotency, bulk updates assets, updates batch status -> Frontend polling detects status change.

## 4. PostgreSQL Schema Changes

### 4.1 New enrichment_data Column

ALTER TABLE assets ADD COLUMN enrichment_data JSONB DEFAULT cast(chr(123)+chr(125) as jsonb). This guarantees a valid JSON object (no null-checking in React).

### 4.2 New enrichment_batches Table

CREATE TABLE with id CHAR(26) PK, session_id FK to sessions, asset_ids CHAR(26)[] NOT NULL, status VARCHAR(20) DEFAULT DISPATCHED with CHECK (DISPATCHED, COMPLETED, PARTIAL, FAILED), dispatched_at and completed_at TIMESTAMPTZ.

Properties: idempotency guard, observability, retry support, type parity with ULID columns, CHECK constraint, no junction table.

## 5. Outbound - Enrich Endpoint

POST /api/sessions/{session_id}/enrich with { asset_ids: [...] }. Returns 202 with { batch_id, asset_count }.

Flow: validate session (404) -> load assets filtered to PENDING/CONFIRMED (422 if empty) -> create batch DISPATCHED -> mark assets PROCESSING -> queue BackgroundTask -> return 202.

Background task uses shared httpx.AsyncClient. Payload includes session_id, batch_id, callback_url (assembled from settings), and hydrated assets array. Compensating transaction on failure: batch FAILED, assets reverted to PENDING.

Enrichable filter: only PENDING and CONFIRMED. INTERNAL blocked (DLP). PROCESSING prevents double-dispatch.

## 6. Inbound - n8n Callback

POST /api/callbacks/n8n with { session_id, batch_id, results: [{ asset_id, status, threat_intel }] }. Returns 200 with { batch_id, updated }.

Flow: lookup batch (404 / idempotency if COMPLETED) -> validate asset_ids in batch -> single-transaction bulk update (status + enrichment_data, WHERE PROCESSING guard) -> determine batch outcome (COMPLETED/PARTIAL/FAILED) -> return.

Properties: idempotency, single transaction, PROCESSING guard, CRITICAL threshold in n8n, no auth (cockpit-net only).


## 7. Pydantic Schemas

File: apps/middleware-api/app/schemas/enrichment.py (new)

EnrichRequest: asset_ids list[str]
EnrichResponse: batch_id str, asset_count int
EnrichmentResult: asset_id str, status Literal[ENRICHED, CRITICAL], threat_intel dict[str, Any]
N8nCallbackRequest: session_id str, batch_id str, results list[EnrichmentResult]
N8nCallbackResponse: batch_id str, updated int

## 8. Configuration

Settings additions: n8n_webhook_url (default http://n8n-orchestrator:5678/webhook/enrich), middleware_internal_url (default http://middleware-api:8000).

## 9. Docker Infrastructure

### 9.1 n8n Service

n8nio/n8n:1.94.1 pinned. Ports 5678. Env: N8N_HOST, N8N_PORT, N8N_PROTOCOL, WEBHOOK_URL, VT_API_KEY (graceful default), ABUSEIPDB_API_KEY. Volumes: n8n_data persistent + ./infrastructure/n8n/workflows bind mount. Depends on middleware-api. cockpit-net.

### 9.2 Middleware Env Vars

SECCENTER_N8N_WEBHOOK_URL and SECCENTER_MIDDLEWARE_INTERNAL_URL.

### 9.3 Workflow IaC

infrastructure/n8n/workflows/README.md with n8n CLI export/import commands.

### 9.4 Network

web-ui:3000 -> middleware-api:8000 -> n8n-orchestrator:5678 (callback back). middleware-api -> postgres-db:5432.


## 10. Frontend Changes

### 10.1 API Client
enrichAssets(sessionId, assetIds) and getSession(sessionId) added to apiClient.

### 10.2 AssetTable
Checkbox column (PENDING/CONFIRMED selectable). Enrich Selected button. Select All Enrichable header checkbox. On click: enrichAssets -> optimistic PROCESSING -> clear selection.

### 10.3 Status Badges
PROCESSING: blue + spinner (read-only). ENRICHED: green (read-only). CRITICAL: orange/amber (read-only). Existing badges unchanged.

### 10.4 Polling
useEffect driven by hasProcessingAssets boolean. 5s interval. Auto-stops when no PROCESSING. React manages lifecycle, Zustand stays pure data.

### 10.5 Zustand Store
markAssetsProcessing(sessionId, assetIds) and refreshSessionAssets(sessionId, assets) actions.

### 10.6 Types
AnalyzedAsset gets enrichment_data: Record<string, unknown>. No rendering in Phase 2B.

## 11. SQLAlchemy Changes

AssetModel: enrichment_data JSONB column with server_default.
New EnrichmentBatchModel: id, session_id FK, asset_ids ARRAY, status, dispatched_at, completed_at.

## 12. File Change Summary

Backend: init.sql (schema), models.py (enrichment_data + batch model), repository.py (batch CRUD), schemas/enrichment.py (new), router/enrichment.py (new), router/callbacks.py (new), services/n8n_dispatcher.py (new), config.py (settings), main.py (routers + httpx).

Frontend: apiClient.ts (2 methods), AssetTable.tsx (selection + button + badges), sessionStore.ts (2 actions), types/index.ts (enrichment_data).

Infrastructure: docker-compose.yml (n8n service), .env.example (new), workflows/README.md (new).

Tests: test_enrichment_endpoint.py, test_callback_endpoint.py, test_n8n_dispatcher.py (all new).

## 13. Scope Boundary

In scope: DB schema, enrich endpoint, callback endpoint, dispatcher, n8n container, frontend (selection, button, badges, polling), Zustand extensions, httpx lifecycle, tests.

Out of scope: n8n workflow creation (CLAUDE.md), WebSocket (Phase 3), enrichment display (Phase 3), callback auth (Phase 4), batch admin UI (Phase 4), rate limits (n8n canvas), retry UI (Phase 3).
