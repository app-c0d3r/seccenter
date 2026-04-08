"""Pydantic schemas for enrichment dispatch and n8n callback."""

from typing import Any, Literal

from pydantic import BaseModel


class EnrichRequest(BaseModel):
    """Request body for POST /api/sessions/{id}/enrich."""
    asset_ids: list[str]


class EnrichResponse(BaseModel):
    """Response for successful enrichment dispatch."""
    batch_id: str
    asset_count: int


class EnrichmentResult(BaseModel):
    """Single asset result from n8n callback."""
    asset_id: str
    status: Literal["ENRICHED", "CRITICAL"]
    threat_intel: dict[str, Any]


class N8nCallbackRequest(BaseModel):
    """Request body from n8n callback POST /api/callbacks/n8n."""
    session_id: str
    batch_id: str
    results: list[EnrichmentResult]


class N8nCallbackResponse(BaseModel):
    """Response after processing n8n callback."""
    batch_id: str
    updated: int
