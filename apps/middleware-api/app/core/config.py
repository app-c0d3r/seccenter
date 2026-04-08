"""Anwendungskonfiguration via Pydantic Settings."""

from pydantic_settings import BaseSettings


class Einstellungen(BaseSettings):
    """Zentrale Konfigurationsklasse – Werte werden aus Umgebungsvariablen geladen."""

    # Datenbankverbindung (asyncpg-Treiber)
    datenbank_url: str = (
        "postgresql+asyncpg://cockpit_user:cockpit_pass@localhost:5432/security_cockpit"
    )

    # Erlaubte CORS-Ursprünge
    cors_urspruenge: list[str] = ["http://localhost:3000"]

    # Maximale Upload-Groesse in Bytes (Standard: 10 MB)
    max_upload_bytes: int = 10 * 1024 * 1024

    model_config = {"env_prefix": "SECCENTER_", "env_file": ".env"}

    @property
    def database_url(self) -> str:
        """Alias fuer Kompatibilitaet mit SQLAlchemy-Schicht."""
        return self.datenbank_url

    @property
    def cors_origins(self) -> list[str]:
        """Alias fuer Kompatibilitaet mit FastAPI CORS-Middleware."""
        return self.cors_urspruenge


# Singleton-Instanz
einstellungen = Einstellungen()
