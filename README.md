# SECCENTER

An AI-powered Cyber Security Cockpit for SOC teams. Analysts can upload unstructured data (PDFs, CSVs, tickets), extract security-relevant assets (IPs, domains, hashes), classify them, and enrich them with threat intelligence services.

## Status

**Initialization phase** — architecture documented, implementation starts in Phase 1.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React · Zustand · Tailwind · TanStack Table |
| Middleware | FastAPI or Node.js |
| AI Agent | LangGraph |
| Database | PostgreSQL + pgvector · FalkorDB |
| Orchestration | n8n |
| Infrastructure | Docker · docker-compose |

## Quick Start

```bash
docker-compose up
```

Starts all 6 containers: `postgres-db`, `graph-db`, `middleware-api`, `n8n-orchestrator`, `web-ui`, `ai-agent`.

## Architecture

```
/apps/web-ui         → React · Zustand · Tailwind (3-column layout)
/apps/middleware     → FastAPI/Node.js · DLP logic · WebSocket · n8n callbacks
/apps/agent          → LangGraph service for AI decision logic
/infrastructure      → Docker · n8n workflow JSONs (IaC)
```

**Core workflow:** Upload → Asset extraction → DLP check → Async enrichment (n8n) → AI report → Canvas editing → Save

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — Architecture, DLP model, LangGraph strategy
- [`docs/master-doc.md`](docs/master-doc.md) — Requirements, data models, roadmap
- [`docs/Lastenheft.md`](docs/Lastenheft.md) — Full requirements specification
