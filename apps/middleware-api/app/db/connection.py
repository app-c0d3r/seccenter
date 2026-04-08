"""Datenbankverbindung und Session-Fabrik fuer SQLAlchemy async."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import einstellungen

# Async-Engine erstellen
datenbank_engine = create_async_engine(
    einstellungen.database_url,
    echo=False,  # SQL-Logging deaktiviert (fuer Produktion)
    pool_pre_ping=True,  # Verbindungspruefung vor jeder Nutzung
)

# Session-Fabrik konfigurieren
AsyncSitzungsFabrik = async_sessionmaker(
    bind=datenbank_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-Dependency: liefert eine Datenbankverbindung und schliesst sie danach."""
    async with AsyncSitzungsFabrik() as sitzung:
        yield sitzung
