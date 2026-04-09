"""Datenbankverbindung und Session-Fabrik fuer SQLAlchemy async."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Async-Engine erstellen
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# Session-Fabrik konfigurieren
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-Dependency: liefert eine Datenbankverbindung und schliesst sie danach."""
    async with async_session_factory() as session:
        yield session
