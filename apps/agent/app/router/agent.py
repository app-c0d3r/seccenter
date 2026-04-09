"""SSE streaming endpoints for the analyst agent."""

import json

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agent.graph import analyst_graph, build_layer1_messages, build_layer2_messages

agent_router = APIRouter(prefix="/api/agent", tags=["agent"])


class AnalyzeRequest(BaseModel):
    """Request body for Layer 1 automated analysis."""
    session_id: str
    session_context: dict
    messages: list[dict] = []
    report_draft: dict = {"header": {}, "body": {}, "foot": {}}


class ChatRequest(BaseModel):
    """Request body for Layer 2 conversational refinement."""
    session_id: str
    session_context: dict
    messages: list[dict]
    report_draft: dict
    user_message: str


async def _stream_agent_response(initial_state: dict):
    """Async generator that yields SSE events from the agent graph."""
    try:
        async for event in analyst_graph.astream_events(initial_state, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                # Streaming token from LLM
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield {"event": "token", "data": json.dumps({"content": chunk.content})}

            elif kind == "on_tool_start":
                # Agent is calling a tool
                yield {
                    "event": "tool_call",
                    "data": json.dumps({"tool": event["name"]}),
                }

            elif kind == "on_tool_end":
                # Tool finished — check for report data
                output = event["data"].get("output", "")
                try:
                    result = json.loads(output) if isinstance(output, str) else output
                except (json.JSONDecodeError, TypeError):
                    result = {}

                # Full report from generate_report
                if all(k in result for k in ("header", "body", "foot")):
                    yield {
                        "event": "report_draft",
                        "data": json.dumps(result),
                    }
                # Partial update from update_report_section
                elif any(k in result for k in ("header", "body", "foot")):
                    yield {
                        "event": "report_section",
                        "data": json.dumps(result),
                    }

        yield {"event": "done", "data": json.dumps({"status": "complete"})}

    except Exception as exc:
        yield {"event": "error", "data": json.dumps({"message": str(exc)})}


@agent_router.post("/analyze")
async def analyze_session(request: AnalyzeRequest) -> EventSourceResponse:
    """Layer 1: Automated report generation via SSE stream."""
    messages = build_layer1_messages(request.session_context)
    initial_state = {
        "messages": messages,
        "session_id": request.session_id,
        "session_context": request.session_context,
        "report_draft": request.report_draft,
        "tool_errors": [],
    }
    return EventSourceResponse(_stream_agent_response(initial_state))


@agent_router.post("/chat")
async def chat_with_agent(request: ChatRequest) -> EventSourceResponse:
    """Layer 2: Conversational refinement via SSE stream."""
    messages = build_layer2_messages(
        session_context=request.session_context,
        chat_history=request.messages,
        report_draft=request.report_draft,
        user_message=request.user_message,
    )
    initial_state = {
        "messages": messages,
        "session_id": request.session_id,
        "session_context": request.session_context,
        "report_draft": request.report_draft,
        "tool_errors": [],
    }
    return EventSourceResponse(_stream_agent_response(initial_state))
