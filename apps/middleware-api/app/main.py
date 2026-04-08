"""FastAPI-Anwendungs-Einstiegspunkt fuer die SECCENTER Middleware API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.connection import engine
from app.router import dlp, sessions, uploads


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startet und beendet die Datenbankverbindung mit der App."""
    yield
    # Datenbankverbindungen beim Herunterfahren schliessen
    await engine.dispose()


# FastAPI-Anwendungsinstanz erstellen
app = FastAPI(
    title="SECCENTER Middleware API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS-Middleware mit konfigurierten Urspruengen hinzufuegen
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router registrieren
app.include_router(sessions.router)
app.include_router(uploads.router)
app.include_router(dlp.router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Gibt den Betriebsstatus der API zurueck."""
    return {"status": "ok"}
