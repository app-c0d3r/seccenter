# SECCENTER

KI-gestütztes Cyber Security Cockpit für SOC-Teams. Analysten können unstrukturierte Daten (PDFs, CSVs, Tickets) hochladen, sicherheitsrelevante Assets (IPs, Domains, Hashes) extrahieren, klassifizieren und mit Threat-Intelligence-Diensten anreichern lassen.

## Status

**Initialisierungsphase** — Architektur dokumentiert, Implementierung folgt in Phase 1.

## Stack

| Schicht | Technologie |
|---|---|
| Frontend | React · Zustand · Tailwind · TanStack Table |
| Middleware | FastAPI oder Node.js |
| KI-Agent | LangGraph |
| Datenbank | PostgreSQL + pgvector · FalkorDB |
| Orchestrierung | n8n |
| Infrastruktur | Docker · docker-compose |

## Schnellstart

```bash
docker-compose up
```

Startet alle 6 Container: `postgres-db`, `graph-db`, `middleware-api`, `n8n-orchestrator`, `web-ui`, `ai-agent`.

## Architektur

```
/apps/web-ui         → React · Zustand · Tailwind (3-Spalten-Layout)
/apps/middleware     → FastAPI/Node.js · DLP-Logik · WebSocket · n8n-Callbacks
/apps/agent          → LangGraph-Service für KI-Entscheidungslogik
/infrastructure      → Docker · n8n-Workflow-JSONs (IaC)
```

**Kern-Workflow:** Upload → Asset-Extraktion → DLP-Check → Async-Enrichment (n8n) → KI-Report → Canvas-Editing → Speichern

## Dokumentation

- [`docs/architecture.md`](docs/architecture.md) — Architektur, DLP-Modell, LangGraph-Strategie
- [`docs/master-doc.md`](docs/master-doc.md) — Anforderungen, Datenmodelle, Roadmap
- [`docs/Lastenheft.md`](docs/Lastenheft.md) — Vollständiges Lastenheft
