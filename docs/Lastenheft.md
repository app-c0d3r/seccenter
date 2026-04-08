### Ergänzung 1: Das Lastenheft (Requirements Specification)

*Dieser Teil kommt in der Dokumentation ganz an den Anfang, noch vor der Architektur.*

### 1. Ausgangslage & Problemstellung

Security-Analysten in einem SOC (Security Operations Center) verbringen einen Großteil ihrer Zeit mit manueller Copy-Paste-Arbeit: IP-Adressen und Hashes müssen aus PDFs oder Tickets kopiert, intern auf Relevanz geprüft und anschließend in externen Threat-Intelligence-Tools (wie VirusTotal) gesucht werden. Dieser Prozess ist zeitaufwendig, fehleranfällig und birgt die Gefahr, dass interne, vertrauliche Daten (Data Leakage) versehentlich an öffentliche APIs gesendet werden.

### 2. Zielgruppe (User Persona)

- **Der Security Analyst:** Arbeitet parallel an mehreren Incidents, benötigt schnelle Fakten, verlässt sich nicht blind auf KI-Entscheidungen und braucht eine effiziente UI für Ad-hoc-Recherchen und das Erstellen von Reports.

### 3. Funktionale Anforderungen (Was muss das System können?)

- **Datei-Verarbeitung:** Das System muss unstrukturierte Indikatoren (IOCs) aus Texten sowie hochgeladenen Dateien (`.txt`, `.csv`, `.pdf`, `.md`) extrahieren können.
- **Asset Management:** Extrahierte Assets (IPs, Domains, Hashes, E-Mails) müssen in einer editierbaren Übersicht dargestellt, vom Analysten korrigiert und dediziert für Analysen ausgewählt werden können.
- **Datenanreicherung (Enrichment):** Das System muss modular externe Dienste anbinden (Minimum für V1: `VirusTotal`, `AbuseIPDB`, `urlscan.io`), um öffentliche Assets anzureichern.
- **KI-gestützte Report-Generierung:** Das System muss die gesammelten Daten via LLM in einem strengen Schema (Header, Body, Conclusion, Next Steps) zusammenfassen und in einem editierbaren Markdown-Canvas bereitstellen.
- **Chat with Data:** Analysten müssen in der Lage sein, mit vergangenen Analysen und der Asset-Datenbank via Chat zu interagieren (RAG), ohne neue Tickets zu generieren.
- **Multitasking:** Das Cockpit muss die parallele Bearbeitung mehrerer unabhängiger Sessions (Fälle) unterstützen.

### 4. Nicht-funktionale Anforderungen (Qualitätsziele)

- **Security First (DLP):** Das System muss deterministisch garantieren, dass Assets, die auf internen Whitelists oder in internen IP-Ranges liegen, niemals an externe APIs übermittelt werden.
- **Performante UI:** Die Web-Oberfläche muss asynchron arbeiten. Lange API-Wartezeiten dürfen die UI nicht blockieren (WebSocket-Streaming).
- **Nachvollziehbarkeit:** Alle automatisierten Aktionen und KI-Antworten müssen auf nachvollziehbaren Fakten aus der Datenbank oder den Enrichment-Tools basieren.