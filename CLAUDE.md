# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt-Info

- **Projektname:** SECCENTER — KI-gestütztes Cyber Security Cockpit für SOC-Teams
- **Status:** Initialisierungsphase (noch kein Source Code vorhanden)
- **Stack:** React + Zustand + Tailwind (web-ui) · FastAPI oder Node.js (middleware) · LangGraph (ai-agent) · PostgreSQL + pgvector · FalkorDB · n8n
- **Start:** `docker-compose up` (startet alle 6 Container)
- **Build/Test/Lint:** Noch nicht definiert — werden in Phase 1 (Foundation & MVP) festgelegt
- **CODE and COMMENTs** write Code and Comments always in english only in every file 
## Architektur

Das System ist eine Docker-basierte Microservices-Architektur im Monorepo:

```
/apps/web-ui         → React · Zustand · Tailwind (3-Spalten-Layout)
/apps/middleware     → FastAPI/Node.js · DLP-Logik · WebSocket · n8n-Callbacks
/apps/agent          → LangGraph-Service für KI-Entscheidungslogik
/infrastructure      → Docker · n8n-Workflow-JSONs (IaC)
```

**Container:** `postgres-db` → `graph-db` (FalkorDB) → `middleware-api` → `n8n-orchestrator` → `web-ui` + `ai-agent`

### Nicht verhandelbare Architekturprinzipien

1. **DLP (Data Leakage Prevention):** Das LLM entscheidet NIEMALS über interne vs. öffentliche Assets. Die Middleware prüft deterministisch via CIDR-Blöcke und Whitelists. Intern getaggte Assets werden auf Code-Ebene für externe API-Aufrufe blockiert.

2. **3-Spalten-UI:**
   - Links: Navigation, Session-Historie
   - Mitte: KI-Chat
   - Rechts (Tabs): Asset Control Center (TanStack Table) + Report Canvas (Markdown-Editor)

3. **Session-Multitasking:** Zustand kapselt Chat-Historie, Staging-Assets und Canvas-Inhalt pro Session. Tabs wechseln Kontext verzögerungsfrei.

4. **Asynchrones n8n:** Middleware antwortet sofort mit `HTTP 202 Accepted`, n8n sendet Enrichment-Ergebnisse via Callback-Webhook zurück.

5. **Structured Outputs:** LLM wird via JSON Schema gezwungen, exakt `{header, body, foot}` zurückzugeben — nie Freitext.

6. **IDs:** Alle Entitäten verwenden UUID/ULID.

7. **LLM-Schnittstelle:** OpenAI-kompatibel — funktioniert mit OpenRouter, Claude API und lokalem Ollama ohne Code-Änderungen.

8. **n8n-Workflows:** Werden manuell im n8n-Canvas gebaut, als JSON in `/infrastructure` abgelegt und beim Docker-Start automatisch geladen. Claude schreibt keine n8n-Workflows.

### Kern-Workflow (Analysten-Pfad)

Upload → Asset-Extraktion → Staging/Dedupe → **DLP-Check (deterministisch)** → Async-Enrichment (n8n → VirusTotal/AbuseIPDB) → LangGraph-Report → Canvas-Editing → Speichern

## Wichtige Docs

| Datei                       | Inhalt                                                    |
| --------------------------- | --------------------------------------------------------- |
| `docs/architecture.md`      | Vollständige Architektur, DLP-Modell, LangGraph-Strategie |
| `docs/master-doc.md`        | Anforderungen, Datenmodelle, Roadmap                      |
| `docs/control-center-ui.md` | `AssetStatus`-Enum, `AnalyzedAsset`-Interface             |
| `docs/output-schemata.md`   | Report-Output-Schema `{header, body, foot}`               |
| `docs/repo-struct.md`       | Geplante Verzeichnisstruktur                              |

## Coding-Regeln (IMMER einhalten)

- Kommentare und Variablennamen auf Deutsch
- Maximale Dateigröße: 300 Zeilen — bei Überschreitung aufteilen
- Keine `any` in TypeScript
- Commits: immer mit `feat:`, `fix:`, `chore:`, `docs:` Prefix
- Kein direktes Arbeiten auf `main` oder `master` Branch
- Neue Packages nur nach ausdrücklicher Genehmigung installieren

## Was Claude NIEMALS tun darf

- Umgebungsvariablen-Dateien oder Zugangsdaten lesen oder bearbeiten
- Direkt auf `main`/`master` pushen oder committen
- Produktions-Konfigurationen ändern
- API-Keys oder Passwörter in Code schreiben
- Dateien außerhalb des Projekts ändern

## Sub-Agent Routing Regeln

- 3+ unabhängige Aufgaben → Sub-Agents parallel starten
- Aufgabe braucht Hauptkontext → direkt im Hauptagent lösen
- Große Codebase durchsuchen → Explore Agent verwenden
- Wiederholende Technik erkannt → Skill erstellen
- Isolierte Expertenaufgabe → Sub-Agent + passender Skill

## Memory & Kontext

- Wenn Context Window voll wird: `/compact` nutzen
- Wichtige Erkenntnisse in `.claude/memory/` festhalten
- Projektspezifische Muster sofort als Skill anlegen
