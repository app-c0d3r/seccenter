# Cyber Security Cockpit – Master Project Specification

## 1. Executive Summary & Projektvision

Das **Cyber Security Cockpit** ist eine moderne, KI-gestützte Web-Anwendung für Security Operations Center (SOC). Es löst das Problem des manuellen und fehleranfälligen "Copy-Paste"-Workflows bei der Untersuchung von Sicherheitsvorfällen. Das System ermöglicht es Analysten, unstrukturierte Daten hochzuladen, sicherheitsrelevante Indikatoren (IOCs) automatisiert zu extrahieren, diese sicher von internen Daten zu trennen und über externe Dienste anzureichern. Das Ergebnis ist ein strukturierter, durch lokale KI aufbereiteter Bericht. Höchste Priorität haben dabei **Datensicherheit (Data Leakage Prevention)** und eine **performante, unterbrechungsfreie Benutzererfahrung**.

---

## 2. Lastenheft (Requirements Specification)

### 2.1 Ausgangslage & Problemstellung

Security-Analysten verbringen zu viel Zeit damit, Indikatoren (IPs, Hashes, Domains) aus unstrukturierten Texten, PDFs oder CSVs zu extrahieren. Diese müssen manuell auf Relevanz geprüft und in externen Threat-Intelligence-Tools (z. B. VirusTotal) gesucht werden. Dabei besteht stets die Gefahr des **Data Leakage** – das versehentliche Senden interner, vertraulicher Assets an öffentliche APIs.

### 2.2 Zielgruppe (User Persona)

- **Der Security Analyst:** Arbeitet oft an mehreren Incidents parallel. Benötigt Fakten statt KI-Halluzinationen. Möchte die volle Kontrolle über extrahierte Daten behalten, fehlerhafte Erkennungen korrigieren und schnell durch historische Daten suchen, ohne zwingend neue Tickets anlegen zu müssen.

### 2.3 Funktionale Anforderungen

- **Upload & Extraktion:** Verarbeitung von `.txt`, `.csv`, `.pdf` und `.md`. Hochpräzise IOC-Extraktion (inklusive Defanging-Auflösung, z. B. `hXXp://`).
- **Asset Management (Staging Area):** Übersichtliche Tabellendarstellung extrahierter Assets. Der Analyst kann Typen (z. B. IP vs. Domain) korrigieren, Assets löschen und spezifische Einträge für das Enrichment markieren.
- **Orchestrierte Datenanreicherung:** Anbindung externer Dienste (VirusTotal, AbuseIPDB, urlscan.io) über modulare, austauschbare Workflows.
- **KI-gestütztes Reporting:** Automatisches Erstellen von Zusammenfassungen in einem strengen Schema (Header, Body, Foot) in einem direkt editierbaren Markdown-Canvas.
- **Chat with Data (RAG):** Ein Chat-Interface zur Abfrage von historischen Analysen und Bestandsdaten (ohne externe API-Calls).
- **Multitasking (Sessions):** Das System unterstützt mehrere parallele Analyse-Workspaces (Tabs), zwischen denen der Analyst ohne Ladezeiten wechseln kann.
- **Command Palette:** Eine globale Suche (Cmd+K) zum schnellen Prüfen von Einzel-Assets ohne Session-Wechsel.

### 2.4 Nicht-funktionale Anforderungen (Qualitätsziele)

- **Security First (DLP):** Die Trennung von `[internal-assets]` und `[public-assets]` erfolgt absolut deterministisch. Interne Assets dürfen das System niemals in Richtung externer APIs verlassen.
- **Performance:** Das UI arbeitet asynchron via WebSockets. API-Timeouts dürfen die Benutzeroberfläche niemals einfrieren.
- **Transparenz:** Nachvollziehbare Zustände für jedes Asset (z. B. *Pending, Processing, Enriched, Internal, Critical*).

---

## 3. Pflichtenheft (System Design & Architecture)

Das Projekt wird als **Docker-basiertes Monorepo** umgesetzt, um eine saubere Trennung der Verantwortlichkeiten (Separation of Concerns) zu gewährleisten.

### 3.1 Die Container-Topologie

- `postgres-db`: Speichert Metadaten, Asset-Verwaltung (White-/Blacklists) und Vektor-Embeddings via `pgvector`.
- `graph-db`: FalkorDB (In-Memory) zur blitzschnellen Ermittlung von historischen Asset-Korrelationen über Cypher-Queries.
- `middleware-api`: Zentrales Backend (Python/FastAPI oder Node.js).
- `n8n-orchestrator`: Führt externe API-Aufrufe aus.
- `ai-agent`: Kapselt die LangGraph-Logik und das LLM-Routing.
- `web-ui`: Moderne React-Applikation.

### 3.2 Deterministische Security (DLP)

- **KI-Einschränkung:** Das LLM trifft **keine** Entscheidungen über das Routing von Assets.
- **Middleware-Logik:** Die Middleware gleicht extrahierte Assets gegen interne CIDR-Ranges und FQDNs in der PostgreSQL-Datenbank ab. Als `internal` markierte Assets werden auf Code-Ebene für n8n blockiert.

### 3.3 Orchestrierung (n8n)

- **Asynchrone Webhooks:** Die Middleware sendet Requests an n8n. n8n antwortet sofort mit HTTP 202 und liefert die finalen Ergebnisse asynchron an einen Callback-Endpoint zurück (Streaming-Konzept).
- **Batching & Pacing:** n8n-Workflows verarbeiten Assets in kleinen Blöcken mit Wartezeiten (Wait-Nodes), um Rate-Limits von Free-Tier-APIs zu respektieren.
- **IaC:** n8n-Workflows werden als JSON im Repository versioniert.

### 3.4 Frontend-Architektur (React)

- **Layout:** 3-Spalten-Design.
    1. *Links:* Navigation & Session-Historie.
    2. *Mitte:* Interaktiver KI-Chat.
    3. *Rechts (Tab-System):* "Asset Control Center" (Staging-Tabelle mit TanStack Table) & "Report Canvas" (editierbarer Markdown-Bericht).
- **State Management:** Verwendung von `Zustand` zur Verwaltung der parallelen Sessions und des Staging-Bereichs.
- **Identifikatoren:** Alle Entitäten nutzen zwingend UUIDs/ULIDs (Ermöglicht URL-Sharing von Tickets).

### 3.5 KI & Agenten-Logik

- **Agnostische LLM-Anbindung:** Kompatibel mit lokalen Modellen (Ollama) und Cloud-APIs (OpenRouter) für maximale Flexibilität beim Testen.
- **Structured Outputs:** Das LLM wird durch die Middleware via JSON-Schema gezwungen, das vorgegebene Berichtsschema exakt einzuhalten. Das Frontend rendert dieses JSON fehlerfrei in das Canvas.

---

## 4. Datenmodellierung (Kern-Strukturen)

Die Basis für den Datenaustausch zwischen Backend und Frontend (TypeScript Interface Skizze)

```json
// Status eines extrahierten Assets in der aktuellen Session
export enum AssetStatus { PENDING, PROCESSING, ENRICHED, INTERNAL, CRITICAL }

// Struktur eines Assets in der UI (Staging Area)
export interface AnalyzedAsset {
  id: string;                // UUID / ULID
  value: string;             // "1.2.3.4"
  type: string;              // IP, DOMAIN, HASH, etc.
  status: AssetStatus;
  enrichmentData?: any;      // Asynchrones JSON-Ergebnis von n8n
  isSelected: boolean;       // UI-State für Batch-Aktionen
}

// Eine isolierte Arbeitsumgebung (Tab) für den Analysten
export interface AnalysisSession {
  sessionId: string;
  chatHistory: ChatMessage[];
  stagedAssets: AnalyzedAsset[];
  canvasContent: string;
}
```

## 5. Projekt-Roadmap

**Phase 1: Foundation & MVP**

- Aufsetzen der Monorepo-Struktur und Docker-Infrastruktur.
- Implementierung des 3-Spalten-Layouts (React) und des Zustand-Stores.
- Basis-Backend für Uploads und simple Extraktion.

**Phase 2: Security & Orchestrierung**

- Aufbau der PostgreSQL-Verwaltung für interne Listen.
- Implementierung der harten DLP-Middleware-Regeln.
- Erstellung robuster n8n-Workflows (Batching) und der Callback-Architektur.

**Phase 3: AI-Integration & RAG**

- Anbindung des LangGraph-Agenten inkl. Structured Outputs für das Canvas.
- Implementierung von pgvector für lokale "Chat with Data"-Suchen.

**Phase 4: Scaling & Vision (Future Scope)**

- Integration der FalkorDB für netzwerkartige Korrelationssuchen.
- Visuelle Graphen in der UI.
- RBAC (Role-Based Access Control).

---

## 6. Entwickler-Richtlinien (KI-Optimierung)

Für alle Coding-Assistenten (Claude Code, Cursor, Copilot) gelten folgende strikte Regeln im Projekt:

- **Token-Sparsamkeit:** Projektstruktur modular halten.
- **Keine Halluzinationen bei der Architektur:** Die in diesem Dokument beschriebene Trennung von Zuständigkeiten (besonders DLP in der Middleware) ist unumstößlich.
- **Professionalität:** Code und Dokumentationen sind sauber zu formatieren und stets professionell zu halten. Vulgärsprache oder abwertende Kommentare im Code sind strengstens untersagt.