"""LangGraph graph definition for the analyst agent."""

import json
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.prompts import ANALYST_SYSTEM_PROMPT, LAYER1_INSTRUCTION, LAYER2_INSTRUCTION
from app.agent.state import AnalystAgentState
from app.agent.tools import generate_report, update_report_section
from app.core.config import settings
from app.core.llm_factory import create_llm

# Tool list (no LLM dependency)
agent_tools = [generate_report, update_report_section]

# Lazy-initialized LLM (avoids crash at import time when no API key is set)
_llm_with_tools = None


def _get_llm_with_tools():
    """Create LLM on first use, not at import time."""
    global _llm_with_tools
    if _llm_with_tools is None:
        llm = create_llm(settings)
        _llm_with_tools = llm.bind_tools(agent_tools)
    return _llm_with_tools


async def agent_node(state: AnalystAgentState) -> dict:
    """Invoke the LLM with the current message history."""
    llm_with_tools = _get_llm_with_tools()
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: AnalystAgentState) -> Literal["tools", "__end__"]:
    """Route to tools if the last message has tool_calls, otherwise end."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "__end__"


def process_tool_results(state: AnalystAgentState) -> dict:
    """Extract report_draft updates from tool results."""
    updates = {}
    for message in reversed(state["messages"]):
        if not isinstance(message, ToolMessage):
            break
        try:
            content = json.loads(message.content) if isinstance(message.content, str) else message.content
        except (json.JSONDecodeError, TypeError):
            continue
        # Check if tool result contains report sections
        for key in ("header", "body", "foot"):
            if key in content:
                updates[key] = content[key]
    if updates:
        return {"report_draft": updates}
    return {}


# Build the graph
graph_builder = StateGraph(AnalystAgentState)
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", ToolNode(agent_tools))
graph_builder.add_node("process_results", process_tool_results)

graph_builder.set_entry_point("agent")
graph_builder.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": END})
graph_builder.add_edge("tools", "process_results")
graph_builder.add_edge("process_results", "agent")

analyst_graph = graph_builder.compile()


def build_layer1_messages(session_context: dict) -> list:
    """Build initial messages for Layer 1 (automated analysis)."""
    context_str = json.dumps(session_context, indent=2)
    return [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=f"{LAYER1_INSTRUCTION}\n\n## Session Context\n\n```json\n{context_str}\n```"),
    ]


def build_layer2_messages(
    session_context: dict,
    chat_history: list[dict],
    report_draft: dict,
    user_message: str,
) -> list:
    """Build messages for Layer 2 (conversational refinement)."""
    context_str = json.dumps(session_context, indent=2)
    draft_str = json.dumps(report_draft, indent=2)

    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"{LAYER2_INSTRUCTION}\n\n"
                f"## Session Context\n\n```json\n{context_str}\n```\n\n"
                f"## Current Report Draft\n\n```json\n{draft_str}\n```"
            )
        ),
    ]

    # Add chat history
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    # Add the new user message
    messages.append(HumanMessage(content=user_message))
    return messages
