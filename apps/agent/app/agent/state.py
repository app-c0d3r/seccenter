"""LangGraph agent state schema for threat analysis."""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


def update_draft(current: dict, update: dict) -> dict:
    """Merge reducer: patches only the keys provided by the tool.

    Prevents update_report_section from overwriting the entire draft
    when only one section changes.
    """
    return {**current, **update}


class AnalystAgentState(TypedDict):
    """State schema for the analyst agent graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    session_context: dict
    report_draft: Annotated[dict, update_draft]
    tool_errors: list[str]
