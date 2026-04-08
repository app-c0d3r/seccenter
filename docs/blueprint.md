### Blaupause für den KI-System-Prompt (`.claudecode`)

Höchste Priorität hat hier die Token-Effizienz. Wenn wir Claude Code oder andere KI-Assistenten im Repository nutzen, dürfen wir keinen unnötigen Kontext mitliefern. Die Anweisungen müssen extrem komprimiert sein.

Der System-Prompt für unser Projekt wird folgende strikte Regeln enthalten:

- **Architektur-Mandat:** Arbeite ausschließlich in der definierten Monorepo-Struktur. Ändere niemals bestehende n8n-Workflows dynamisch via Code; Workflows sind rein manuell erstelltes JSON.
- **Security & DLP (Strikt):** Das LLM trifft keine Entscheidungen über `internal-assets` vs. `public-assets`. Jegliches Routing und Blockieren von externen API-Calls muss hartcodiert in der `middleware-api` erfolgen.
- **UI-Vorgaben:** Das Frontend ist eine moderne React-App. Nutze das 3-Spalten-Layout. Verwende ausschließlich `Zustand` für das globale State-Management (Session-Tabs, editierbares Canvas).
- **Datenbank-Regel:** Nutze für alle Identifikatoren (Tickets, Sessions) zwingend UUIDs oder ULIDs. Schreibe komplexe relationale Abfragen für FalkorDB (Cypher), nutze PostgreSQL für strukturierte Metadaten und Text.
- **Kommunikations-Stil (Code):** Dokumentiere jede Funktion präzise. Keine Platzhalter-Kommentare.
