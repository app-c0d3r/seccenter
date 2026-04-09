"""LangGraph tools for the analyst agent.

Security constraint: No network tools, no DB tools, no file tools.
The agent can only reason about injected context and produce structured output.
"""

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ReportHeader(BaseModel):
    """Structured header section of the threat report."""

    when: str = Field(description="ISO timestamp of the analysis")
    what: str = Field(description="Short summary, max 100 characters")
    who: str = Field(description="Analyst name or System")


class AssetSummaryItem(BaseModel):
    """Single asset finding in the report body."""

    asset_value: str = Field(description="The IOC value (IP, domain, hash)")
    findings: str = Field(description="Summary of enrichment results")


class ReportBody(BaseModel):
    """Structured body section of the threat report."""

    assets_summary: list[AssetSummaryItem] = Field(
        description="List of assets with findings"
    )


class ReportFoot(BaseModel):
    """Structured foot section of the threat report."""

    conclusion: str = Field(description="Overall analysis conclusion")
    next_steps: list[str] = Field(description="Recommended next steps")
    tips_and_measures: list[str] = Field(description="Security tips and measures")


class FullReport(BaseModel):
    """Complete structured report output."""

    header: ReportHeader
    body: ReportBody
    foot: ReportFoot


@tool
def generate_report(
    header_when: str,
    header_what: str,
    header_who: str,
    assets_summary: list[dict[str, str]],
    conclusion: str,
    next_steps: list[str],
    tips_and_measures: list[str],
) -> dict[str, Any]:
    """Generate a structured threat report with header, body, and foot sections.

    Call this after analyzing the session context to produce the final report.
    """
    return {
        "header": {"when": header_when, "what": header_what, "who": header_who},
        "body": {"assets_summary": assets_summary},
        "foot": {
            "conclusion": conclusion,
            "next_steps": next_steps,
            "tips_and_measures": tips_and_measures,
        },
    }


@tool
def update_report_section(
    section: str,
    content: dict[str, Any],
) -> dict[str, Any]:
    """Update a specific section (header, body, or foot) of the report draft."""
    if section not in ("header", "body", "foot"):
        return {"error": f"Invalid section: {section}. Must be header, body, or foot."}
    return {section: content}
