"""Anwendungskonfiguration via Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Zentrale Konfigurationsklasse – Werte werden aus Umgebungsvariablen geladen."""

    # Datenbankverbindung (asyncpg-Treiber)
    database_url: str = (
        "postgresql+asyncpg://cockpit_user:cockpit_pass@localhost:5432/security_cockpit"
    )

    # Erlaubte CORS-Urspruenge
    cors_origins: list[str] = ["http://localhost:3000"]

    # Maximale Upload-Groesse in Bytes (Standard: 10 MB)
    max_upload_bytes: int = 10 * 1024 * 1024

    # n8n webhook URL for enrichment dispatch
    n8n_webhook_url: str = "http://n8n-orchestrator:5678/webhook/enrich"

    # Internal URL of this middleware (for callback_url in n8n payload)
    middleware_internal_url: str = "http://middleware-api:8000"

    model_config = {"env_prefix": "SECCENTER_", "env_file": ".env"}


# Singleton-Instanz
settings = Settings()
