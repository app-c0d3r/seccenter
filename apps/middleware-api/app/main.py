"""FastAPI application entry point for the SECCENTER Middleware API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.connection import async_session_factory, engine
from app.router import callbacks, dlp, enrichment, sessions, uploads
from app.services.dlp_classifier import dlp_classifier


# Module-level httpx client for background tasks
http_client: httpx.AsyncClient = None  # type: ignore[assignment]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start and stop database connection and httpx client with the app."""
    global http_client
    # Load DLP rules into memory at startup
    async with async_session_factory() as db:
        await dlp_classifier.load(db)
    # Create shared httpx client
    http_client = httpx.AsyncClient()
    yield
    # Cleanup: close httpx client, then database connections
    await http_client.aclose()
    await engine.dispose()


# FastAPI application instance
app = FastAPI(
    title="SECCENTER Middleware API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware with configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(sessions.router)
app.include_router(uploads.router)
app.include_router(dlp.router)
app.include_router(enrichment.router)
app.include_router(callbacks.router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return API operational status."""
    return {"status": "ok"}
