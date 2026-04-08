"""Router for n8n enrichment callback endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.db.connection import get_db
from app.schemas.enrichment import N8nCallbackRequest, N8nCallbackResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/callbacks", tags=["callbacks"])


@router.post("/n8n", response_model=N8nCallbackResponse)
async def n8n_callback(
    body: N8nCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> N8nCallbackResponse:
    """Receive enrichment results from n8n and update assets."""
    # Lookup batch
    batch = await repository.get_enrichment_batch(db, body.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Idempotency: if batch already completed, return immediately
    if batch.status == "COMPLETED":
        return N8nCallbackResponse(batch_id=body.batch_id, updated=0)

    # Process results
    updated_count = 0
    batch_asset_ids = set(batch.asset_ids)

    for result in body.results:
        # Skip unknown asset IDs not in this batch
        if result.asset_id not in batch_asset_ids:
            logger.warning(
                "Callback for batch %s: asset %s not in batch, skipping",
                body.batch_id, result.asset_id,
            )
            continue

        # Update asset (PROCESSING guard in repository)
        success = await repository.update_asset_enrichment(
            db, result.asset_id, result.status, result.threat_intel
        )
        if success:
            updated_count += 1

    # Determine batch outcome
    all_error = all("error" in r.threat_intel for r in body.results) and len(body.results) > 0
    if all_error:
        batch_status = "FAILED"
    elif len(body.results) < len(batch.asset_ids):
        batch_status = "PARTIAL"
    else:
        batch_status = "COMPLETED"

    await repository.update_batch_status(db, body.batch_id, batch_status)
    await db.commit()

    return N8nCallbackResponse(batch_id=body.batch_id, updated=updated_count)
