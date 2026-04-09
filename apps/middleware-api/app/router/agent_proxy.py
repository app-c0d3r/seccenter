"""SSE proxy routes for the AI agent with DLP masking."""

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.connection import get_db
from app.db.repository import get_session_with_assets
from app.services.dlp_masking import DLPMaskingContext

router = APIRouter(prefix="/api/sessions", tags=["agent"])


def _build_session_context(session, assets) -> dict:
    """Build the session context payload for the agent."""
    return {
        "session_name": session.name,
        "assets": [
            {
                "id": asset.id,
                "value": asset.value,
                "type": asset.type,
                "status": asset.status,
                "enrichment_data": asset.enrichment_data or {},
            }
            for asset in assets
        ],
    }


async def _proxy_agent_stream(
    agent_url: str,
    payload: dict,
    masking_ctx: DLPMaskingContext,
):
    """SSE proxy generator with content-aware DLP unmasking.

    Handles two levels of chunking:
    Level 1 - SSE event boundaries: buffer until complete events (double newline)
    Level 2 - LLM tokenization splits: buffer token events with incomplete
              [INTERNAL_*] tokens
    """
    token_buffer = ""

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        async with client.stream("POST", agent_url, json=payload) as response:
            if response.status_code != 200:
                await response.aread()
                yield (
                    f"event: error\ndata: "
                    f"{json.dumps({'message': f'Agent returned {response.status_code}'})}"
                    f"\n\n"
                )
                return

            sse_buffer = ""
            async for chunk in response.aiter_text():
                sse_buffer += chunk

                # Level 1: Process complete SSE events (delimited by \n\n)
                while "\n\n" in sse_buffer:
                    event_str, sse_buffer = sse_buffer.split("\n\n", 1)
                    event_str = event_str.strip()
                    if not event_str:
                        continue

                    # Parse SSE event fields
                    event_type = ""
                    data_str = ""
                    for line in event_str.split("\n"):
                        if line.startswith("event:"):
                            event_type = line[len("event:"):].strip()
                        elif line.startswith("data:"):
                            data_str = line[len("data:"):].strip()

                    if not event_type or not data_str:
                        continue

                    # Route by event type
                    if event_type == "token":
                        # Level 2: Buffer tokens that might contain split
                        # DLP placeholder tokens
                        try:
                            parsed = json.loads(data_str)
                            content = parsed.get("content", "")
                        except (json.JSONDecodeError, TypeError):
                            content = ""

                        token_buffer += content

                        # Check for incomplete DLP token: has [ but no ]
                        last_open = token_buffer.rfind("[")
                        if (
                            last_open != -1
                            and "]" not in token_buffer[last_open:]
                        ):
                            # Hold buffer — might be a split [INTERNAL_*] token
                            continue

                        # Buffer complete — unmask and yield
                        unmasked = masking_ctx.unmask(token_buffer)
                        yield (
                            f"event: token\n"
                            f"data: {json.dumps({'content': unmasked})}\n\n"
                        )
                        token_buffer = ""

                    elif event_type in ("report_draft", "report_section"):
                        # JSON payloads — unmask entire payload
                        unmasked_data = masking_ctx.unmask(data_str)
                        yield (
                            f"event: {event_type}\n"
                            f"data: {unmasked_data}\n\n"
                        )

                    else:
                        # tool_call, done, error — pass through unchanged
                        yield f"event: {event_type}\ndata: {data_str}\n\n"

            # Flush remaining token buffer
            if token_buffer:
                unmasked = masking_ctx.unmask(token_buffer)
                yield (
                    f"event: token\n"
                    f"data: {json.dumps({'content': unmasked})}\n\n"
                )


@router.get("/{session_id}/agent/stream")
async def stream_analysis(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Layer 1: Automated report generation via SSE stream.

    Loads session, masks internal assets, proxies to ai-agent,
    unmasks response tokens before sending to browser.
    """
    session = await get_session_with_assets(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build DLP masking context and mask session context
    masking_ctx = DLPMaskingContext(session.assets)
    context = _build_session_context(session, session.assets)
    masked_context_str = masking_ctx.mask(json.dumps(context))
    masked_context = json.loads(masked_context_str)

    # Build payload for agent
    payload = {
        "session_id": session_id,
        "session_context": masked_context,
        "messages": [],
        "report_draft": {"header": {}, "body": {}, "foot": {}},
    }

    agent_url = f"{settings.agent_url}/api/agent/analyze"

    return StreamingResponse(
        _proxy_agent_stream(agent_url, payload, masking_ctx),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
