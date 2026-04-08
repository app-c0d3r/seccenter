# 🛡️ Cyber Security Cockpit – Projekt- & Architekturdokumentation

## 1. Projektvision & Zielsetzung

Das **Cyber Security Cockpit** ist eine moderne, KI-gestützte Web-Anwendung für Security Operations Center (SOC). Es ermöglicht Analysten, unstrukturierte Daten (z. B. aus Tickets, PDFs, CSVs) hochzuladen, daraus sicherheitsrelevante Assets (IPs, Domains, Hashes) zu extrahieren, diese zu klassifizieren und mit Threat-Intelligence-Diensten anzureichern.
Oberste Priorität haben dabei **Datensicherheit (Data Leakage Prevention)**, eine **hochperformante Benutzererfahrung (UX)** und die **Automatisierung von Routineaufgaben** durch externe Orchestrierung und lokale KI-Modelle.

## 2. Der Kern-Workflow (Analysten-Pfad)

Der Prozess ist auf maximale Effizienz und Kontrolle durch den Analysten ("Human-in-the-Loop") ausgelegt:

1. **Upload & Extraktion:** Der Analyst lädt unstrukturierte Daten (Files/Text) in eine aktive Session hoch. Das Backend extrahiert die Assets hochpräzise (inkl. Defanging-Auflösung).
2. **Staging & Deduplizierung:** Extrahierte Assets werden im Speicher bereinigt und mit der Datenbank abgeglichen (Ist die IP neu? Ist sie Teil der Firmen-Whitelist?).
3. **Review (Asset Control Center):** Der Analyst sieht die Assets in einer interaktiven Tabelle (Status, Typ). Er kann Typen korrigieren, Assets löschen oder markieren.
4. **Enrichment (Asynchron):** Freigegebene öffentliche Assets werden an `n8n` gesendet, welches strukturiert externe APIs (VirusTotal, AbuseIPDB) abfragt.
5. **Report & Canvas:** Ein KI-Agent wertet die Enrichment-Ergebnisse aus und pusht einen strukturierten Bericht in ein editierbares Markdown-Canvas.
6. **Abschluss:** Nach manueller Verfeinerung klickt der Analyst auf "Speichern & Abschließen", wodurch die Ergebnisse revisionssicher in die Datenbank geschrieben werden.

## 3. Architektur & Infrastruktur

Das System ist als **Docker-basierte Microservices-Architektur** konzipiert, organisiert in einem Monorepo für maximale Transparenz und Token-Effizienz (KI-Coding-Assistenten).

### 3.1. Container-Topologie

- `postgres-db`: Relationale Metadaten, Asset-Listen und Vektor-Embeddings (pgvector).
- `graph-db`: FalkorDB (In-Memory Graph) für komplexe Asset-Beziehungen (Cypher-Queries).
- `middleware-api`: Zentrales Backend (Python/FastAPI oder Node.js). Handhabt Uploads, DLP-Regeln, WebSocket-Streaming und API-Routing.
- `n8n-orchestrator`: Führt die asynchrone Datenanreicherung durch.
- `ai-agent`: LangGraph-Service für die KI-Entscheidungslogik.
- `web-ui`: Moderne React-Applikation.

## 4. Sicherheits- & Datenmodell

### 4.1. Deterministische Data Leakage Prevention (DLP)

- **Problem:** LLMs halluzinieren und dürfen keine Freigaben für das Senden von Daten an externe APIs erteilen.
- **Lösung:** Die Trennung von `[internal-assets]` und `[public-assets]` erfolgt **strikt deterministisch in der Middleware**. IPs und Domains werden programmatisch gegen interne CIDR-Blöcke und Whitelists geprüft. Als "intern" getaggte Assets werden auf Code-Ebene für externe API-Aufrufe blockiert.

### 4.2. Hybrides Datenbankdesign

- **PostgreSQL (mit pgvector):** Dient als "Single Source of Truth" für Tickets, Settings, interne Listen (Verwaltung über eine Admin-UI, nicht über fehleranfällige Flat-Files) und historische RAG-Daten ("Chat with Data"). Alle IDs sind zwingend **UUIDs/ULIDs**.
- **FalkorDB:** Ermittelt blitzschnell historische Verknüpfungen (z. B. `(Neu extrahierte IP) -> (Alter Filehash) -> (Vergangener Incident)`).

## 5. Frontend: UI/UX & State Management (React)

### 5.1. Das 3-Spalten-Layout

Das UI ist auf Übersichtlichkeit trotz hoher Informationsdichte optimiert:

1. **Linke Spalte (Navigation):** Menü, Historie und Session-Übersicht.
2. **Mittlere Spalte (Interaktion):** Der KI-Chat für Ad-hoc-Analysen und kontextuelle Anweisungen.
3. **Rechte Spalte (Arbeitsbereich via Tabs):**
    - *Tab 1: Asset Control Center:* Eine hochperformante Tabelle (z. B. TanStack Table) mit Sortier-, Filter- und Editierfunktionen für das Staging von Assets.
    - *Tab 2: Report Canvas:* Ein interaktiver Markdown-Editor, in dem die finalen Analysen live zusammengeführt werden.

### 5.2. Session-basiertes Multitasking

- **Problem:** Analysten bearbeiten oft mehrere Vorfälle parallel.
- **Lösung:** Globale Zustandsverwaltung mit **Zustand**. Eine Session kapselt Chat-Historie, Staging-Assets und Canvas-Inhalt. Der Wechsel zwischen Tabs im Browser/UI tauscht den Kontext verzögerungsfrei aus.
- **Command Palette (Cmd+K):** Für schnelle Suchen ("Ist diese IP bekannt?"), ohne die aktuelle Session verlassen zu müssen.

## 6. Backend, Orchestrierung & KI

### 6.1. Skalierbares n8n-Design

- **Asynchrone Webhooks:** Um Timeouts zu vermeiden, antwortet n8n auf API-Calls der Middleware sofort (`HTTP 202 Accepted`) und sendet die fertigen Enrichment-Daten später via Callback-Endpoint an das System zurück.
- **Pacing & Batching:** Um Rate-Limits von kostenlosen API-Keys (Free Tier) zu respektieren, iteriert n8n über Assets in Batches und nutzt "Wait"-Nodes zur Drosselung.
- **Infrastructure as Code (IaC):** Workflows werden manuell im n8n-Canvas gebaut, als JSON im Repository abgelegt und beim Docker-Start automatisch geladen (Die KI schreibt keine n8n-Workflows).

### 6.2. LLM-Strategie & LangGraph

- **Flexibilität:** Der Service nutzt eine OpenAI-kompatible Schnittstelle, um nahtlos zwischen Cloud-Modellen (OpenRouter/Claude/GPT) und lokalen Modellen (Ollama/Llama3) zu wechseln.
- **Structured Outputs:** Um sicherzustellen, dass die Berichte im Frontend nicht brechen, wird das LLM durch die Middleware (via JSON-Schema / Pydantic) gezwungen, exakt das Schema `{header, body, foot}` zurückzugeben.
- **Lokales RAG:** "Chat with Data" nutzt ausschließlich die lokale PostgreSQL/pgvector-Datenbank, um Unternehmenswissen abzufragen, ohne externe Dienste zu triggern.

## 7. MVP-Abgrenzung (Was vorerst nicht gebaut wird)

Um schnelle Iterationen zu garantieren, wurden folgende Themen für spätere Versionen zurückgestellt:

- Interaktive visuelle Graph-Netzwerke (Cytoscape/D3.js) in der UI (Vorerst nur textbasierte Relationen).
- n8n Queue-Mode mit Redis-Workern (Ein Single-Container reicht für den Start).
- Komplexes Rollen- & Rechtesystem (RBAC / Login). Der MVP läuft vorerst lokal und offen.