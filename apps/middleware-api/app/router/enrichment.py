"""Router for enrichment dispatch endpoint."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.core.config import settings
from app.db import repository
from app.db.connection import async_session_factory, get_db
from app.schemas.enrichment import EnrichRequest, EnrichResponse
from app.services.n8n_dispatcher import dispatch_to_n8n

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["enrichment"])


@router.post("/{session_id}/enrich", status_code=202, response_model=EnrichResponse)
async def enrich_assets(
    session_id: str,
    body: EnrichRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> EnrichResponse:
    """Dispatch selected assets for threat intelligence enrichment via n8n."""
    # Validate session exists
    session = await repository.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load requested assets, filter to enrichable statuses
    assets = await repository.get_assets_by_ids(db, session_id, body.asset_ids)
    enrichable = [a for a in assets if a.status in ("PENDING", "CONFIRMED")]

    if not enrichable:
        raise HTTPException(
            status_code=422, detail="No enrichable assets (only PENDING/CONFIRMED allowed)"
        )

    enrichable_ids = [a.id for a in enrichable]
    batch_id = str(ULID())

    # Create batch and mark assets PROCESSING
    await repository.create_enrichment_batch(db, batch_id, session_id, enrichable_ids)
    await repository.bulk_mark_assets_processing(db, enrichable_ids)

    # Build hydrated payload for n8n
    callback_url = f"{settings.middleware_internal_url}/api/callbacks/n8n"
    payload = {
        "session_id": session_id,
        "batch_id": batch_id,
        "callback_url": callback_url,
        "assets": [
            {"id": a.id, "value": a.value, "type": a.type}
            for a in enrichable
        ],
    }

    # Import http_client from main module (deferred to avoid circular imports)
    from app.main import http_client  # noqa: PLC0415

    # Queue background dispatch
    background_tasks.add_task(
        dispatch_to_n8n,
        http_client=http_client,
        webhook_url=settings.n8n_webhook_url,
        payload=payload,
        batch_id=batch_id,
        asset_ids=enrichable_ids,
        db_session_factory=async_session_factory,
    )

    return EnrichResponse(batch_id=batch_id, asset_count=len(enrichable_ids))
