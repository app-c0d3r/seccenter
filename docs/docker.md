Die Konfiguration wird folgende Container (Services) orchestrieren:

- **`postgres-db`**: Der PostgreSQL-Container mit der `pgvector`Erweiterung. Speichert Tickets, Assets (SQL) und Embeddings für die RAG-Suche. *(Benötigt ein persistentes Volume)*
- **`graph-db`**: Der FalkorDB-Container. Läuft komplett im Arbeitsspeicher, persistiert aber Snapshots auf die Festplatte. Speichert exklusiv die Relationen (z. B. IP -> Hash -> Ticket).
- **`n8n-orchestrator`**: Unser Single-Container-Worker. Wird so konfiguriert, dass er beim Start automatisch die `.json`Workflows aus dem GitHub-Repository lädt (IaC). *(Benötigt ein persistentes Volume für lokale Keys/Settings)*
- **`middleware-api`**: Unser Backend-for-Frontend (z.B. Python/FastAPI). Exponiert die WebSockets für das UI, führt die deterministische Data Leakage Prevention (DLP) durch und managt die Callbacks von n8n.
- **`ai-agent`**: Der LangGraph-Service. Kommuniziert über die Middleware und nutzt Umgebungsvariablen (`BASE_URL`), um zwischen lokalem Ollama und OpenRouter dynamisch zu wechseln.
- **`web-ui`**: Der React-Container. Im Entwicklungsmodus mit Hot-Reloading, im produktiven Deployment als Multi-Stage-Build (kompiliert zu statischen Nginx-Dateien für minimale Image-Größe).