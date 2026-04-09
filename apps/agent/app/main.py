"""FastAPI entry point for the SECCENTER AI Agent service."""

from fastapi import FastAPI

app = FastAPI(title="SECCENTER AI Agent", version="0.1.0")


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return agent operational status."""
    return {"status": "ok"}
