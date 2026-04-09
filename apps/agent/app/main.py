"""FastAPI entry point for the SECCENTER AI Agent service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router.agent import agent_router

app = FastAPI(title="SECCENTER AI Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return agent operational status."""
    return {"status": "ok"}
