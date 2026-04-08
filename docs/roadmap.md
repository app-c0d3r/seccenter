### Ergänzung 2: Die Projekt-Roadmap

*Dieser Teil kommt ans Ende der Dokumentation, um den zeitlichen und logischen Ablauf der Entwicklung darzustellen.*

### Phase 1: Foundation & MVP (Minimum Viable Product)

*Fokus: Kernarchitektur und grundlegender Datenfluss.*

- Aufsetzen der Docker-Infrastruktur (PostgreSQL, n8n, React, FastAPI/Node).
- Implementierung des 3-Spalten-Layouts in React.
- Entwicklung des Zustand-Stores für das Session-Management (Multitasking).
- Backend-Logik für Datei-Uploads und einfache IOC-Extraktion.

### Phase 2: Security & Orchestrierung

*Fokus: Data Leakage Prevention und n8n-Integration.*

- Einrichtung der PostgreSQL-Datenbank für interne Assets (CIDR-Ranges, FQDNs).
- Entwicklung der deterministischen DLP-Middleware (Routing-Logik).
- Aufbau der n8n-Workflows für VirusTotal und AbuseIPDB (inkl. Batching und Pacing zur Schonung von API-Limits).
- Implementierung der asynchronen WebSockets vom Backend zum Frontend-Canvas.

### Phase 3: AI-Integration & RAG

*Fokus: Intelligente Auswertung und Report-Generierung.*

- Anbindung des LangGraph-Agenten (Ollama / OpenRouter).
- Implementierung von *Structured Outputs* (JSON Schema) für das Report-Canvas.
- Aufbau der pgvector-Suche für das "Chat with Data"-Feature.

### Phase 4: Scaling & Vision (Future Scope)

*Fokus: Erweiterte Analysten-Werkzeuge.*

- Integration von FalkorDB für die komplexe, graphenbasierte Korrelation von Assets.
- Interaktive visuelle Graphen in der React-UI (z. B. Maltego-ähnliche Ansichten).
- Rollen- und Berechtigungskonzept (RBAC) für den unternehmensweiten Rollout.