"""Background task for dispatching enrichment batches to n8n."""

import logging

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import repository

logger = logging.getLogger(__name__)


async def dispatch_to_n8n(
    http_client: httpx.AsyncClient,
    webhook_url: str,
    payload: dict,
    batch_id: str,
    asset_ids: list[str],
    db_session_factory: async_sessionmaker,
) -> None:
    """POST hydrated payload to n8n webhook. On failure, run compensating transaction."""
    try:
        response = await http_client.post(webhook_url, json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info("Batch %s dispatched to n8n (status %d)", batch_id, response.status_code)
    except (httpx.HTTPError, httpx.ConnectError) as exc:
        logger.error("Batch %s dispatch failed: %s", batch_id, exc)
        async with db_session_factory() as db:
            await repository.update_batch_status(db, batch_id, "FAILED")
            await repository.bulk_revert_assets_to_pending(db, asset_ids)
        logger.info("Batch %s compensating transaction complete", batch_id)
