# Phase 3: AI Agent + Report Canvas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AI-powered analysis agent (LangGraph in a separate container) and a Report Canvas UI, enabling analysts to generate structured threat reports from enriched session data with one click, then refine via conversational chat.

**Architecture:** A new `ai-agent` Python container runs LangGraph with FastAPI, receiving pre-masked session context from the middleware via internal HTTP. The middleware acts as SSE proxy — masking internal values before the LLM, unmasking in the response stream. The frontend adds a ChatPanel (middle column) and ReportCanvas (right column tab), both powered by SSE streaming via `fetch` + `getReader()`.

**Tech Stack:** Python 3.12, LangGraph, LangChain (langchain-core, langchain-openai, langchain-ollama), FastAPI, uvicorn, httpx (SSE proxy), React 18, Zustand, react-markdown

**Spec:** `docs/superpowers/specs/2026-04-09-phase3-ai-canvas-design.md`

---

## File Structure

### New files — `apps/agent/` (AI agent container)

| File | Responsibility |
|------|----------------|
| `apps/agent/Dockerfile` | Python 3.12-slim image, pip install, uvicorn entrypoint |
| `apps/agent/requirements.txt` | langgraph, langchain-core, langchain-openai, langchain-ollama, fastapi, uvicorn, pydantic-settings |
| `apps/agent/app/__init__.py` | Package marker |
| `apps/agent/app/main.py` | FastAPI app with CORS, router registration |
| `apps/agent/app/core/__init__.py` | Package marker |
| `apps/agent/app/core/config.py` | `AgentSettings` pydantic-settings class (LLM_PROVIDER, LLM_MODEL, etc.) |
| `apps/agent/app/core/llm_factory.py` | `create_llm()` factory returning BaseChatModel |
| `apps/agent/app/agent/__init__.py` | Package marker |
| `apps/agent/app/agent/state.py` | `AnalystAgentState` TypedDict + `update_draft` reducer |
| `apps/agent/app/agent/tools.py` | `read_session_context`, `generate_report`, `update_report_section` |
| `apps/agent/app/agent/prompts.py` | System prompts for threat analysis |
| `apps/agent/app/agent/graph.py` | LangGraph graph definition and compilation |
| `apps/agent/app/router/__init__.py` | Package marker |
| `apps/agent/app/router/agent.py` | `POST /api/agent/analyze` and `POST /api/agent/chat` SSE endpoints |

### New files — `apps/middleware-api/` (SSE proxy + DLP masking)

| File | Responsibility |
|------|----------------|
| `apps/middleware-api/app/services/dlp_masking.py` | `DLPMaskingContext` class — ephemeral mask/unmask map |
| `apps/middleware-api/app/router/agent_proxy.py` | SSE proxy routes: `GET /api/sessions/{id}/agent/stream`, `POST /api/sessions/{id}/agent/chat` |

### New files — `apps/web-ui/src/` (Chat + Canvas UI)

| File | Responsibility |
|------|----------------|
| `apps/web-ui/src/types/agent.ts` | `ChatMessage`, `ReportDraft`, SSE event types |
| `apps/web-ui/src/api/sseClient.ts` | SSE stream consumer using fetch + getReader() |
| `apps/web-ui/src/components/ChatPanel.tsx` | Message list + input, SSE stream consumer |
| `apps/web-ui/src/components/ChatMessage.tsx` | Single message bubble with streaming animation |
| `apps/web-ui/src/components/ReportCanvas.tsx` | Editable header/body/foot sections |
| `apps/web-ui/src/components/AnalyzeButton.tsx` | Triggers Layer 1 automated report generation |

### Modified files

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `ai-agent` service, add `SECCENTER_AGENT_URL` to middleware env |
| `apps/middleware-api/app/core/config.py` | Add `agent_url` setting |
| `apps/middleware-api/app/main.py` | Register `agent_proxy` router |
| `apps/web-ui/package.json` | Add `react-markdown` |
| `apps/web-ui/src/store/sessionStore.ts` | Add `chatMessages`, `reportDraft`, `agentStreaming` state |
| `apps/web-ui/src/layout/CenterPanel.tsx` | Replace placeholder with `ChatPanel` |
| `apps/web-ui/src/layout/RightPanel.tsx` | Enable Report tab, add `ReportCanvas` + `AnalyzeButton` |

---

## Part 1: AI Agent Container (Tasks 1-4)

### Task 1: Docker Infrastructure + Agent Skeleton

**Files:**
- Create: `apps/agent/Dockerfile`
- Create: `apps/agent/requirements.txt`
- Create: `apps/agent/app/__init__.py`
- Create: `apps/agent/app/main.py`
- Create: `apps/agent/app/core/__init__.py`
- Create: `apps/agent/app/core/config.py`
- Create: `apps/agent/app/agent/__init__.py`
- Create: `apps/agent/app/router/__init__.py`
- Modify: `docker-compose.yml`
- Modify: `apps/middleware-api/app/core/config.py`

- [ ] **Step 1: Create agent Dockerfile**

```dockerfile
# apps/agent/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
```

- [ ] **Step 2: Create requirements.txt**

```txt
# apps/agent/requirements.txt
# LangGraph / LangChain
langgraph==0.4.1
langchain-core==0.3.51
langchain-openai==0.3.12
langchain-ollama==0.3.2

# Web framework
fastapi==0.115.0
uvicorn[standard]==0.30.0

# SSE streaming
sse-starlette==2.2.1

# Configuration
pydantic==2.9.0
pydantic-settings==2.5.0
```

- [ ] **Step 3: Create package markers**

Create empty `__init__.py` files:
- `apps/agent/app/__init__.py`
- `apps/agent/app/core/__init__.py`
- `apps/agent/app/agent/__init__.py`
- `apps/agent/app/router/__init__.py`

- [ ] **Step 4: Create AgentSettings config**

```python
# apps/agent/app/core/config.py
"""Agent configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    llm_provider: str = "openrouter"
    llm_model: str = "anthropic/claude-sonnet-4-20250514"
    llm_api_key: str = ""
    llm_base_url: str = ""

    model_config = {"env_prefix": "LLM_"}


settings = AgentSettings()
```

- [ ] **Step 5: Create minimal FastAPI app**

```python
# apps/agent/app/main.py
"""FastAPI entry point for the SECCENTER AI Agent service."""

from fastapi import FastAPI

app = FastAPI(title="SECCENTER AI Agent", version="0.1.0")


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Add ai-agent service to docker-compose.yml**

Add after the `n8n-orchestrator` service block in `docker-compose.yml`:

```yaml
  # LangGraph AI Agent for threat analysis and report generation
  ai-agent:
    build: ./apps/agent
    ports:
      - "8001:8001"
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER:-openrouter}
      - LLM_MODEL=${LLM_MODEL:-anthropic/claude-sonnet-4-20250514}
      - LLM_API_KEY=${LLM_API_KEY:-}
      - LLM_BASE_URL=${LLM_BASE_URL:-}
    depends_on:
      - middleware-api
    networks:
      - cockpit-net
```

Update the `middleware-api` environment section - add:

```yaml
      - SECCENTER_AGENT_URL=http://ai-agent:8001
```

- [ ] **Step 7: Add agent_url to middleware Settings**

In `apps/middleware-api/app/core/config.py`, add this field to the `Settings` class:

```python
    # AI agent service URL (internal network)
    agent_url: str = "http://ai-agent:8001"
```

- [ ] **Step 8: Verify container builds**

Run: `docker compose build ai-agent middleware-api`

Expected: Both images build successfully.

- [ ] **Step 9: Commit**

```bash
git add apps/agent/ docker-compose.yml apps/middleware-api/app/core/config.py
git commit -m "feat: add ai-agent container skeleton with Docker infrastructure"
```

---

### Task 2: LLM Factory + Agent State Schema

**Files:**
- Create: `apps/agent/app/core/llm_factory.py`
- Create: `apps/agent/app/agent/state.py`

- [ ] **Step 1: Create LLM factory**

```python
# apps/agent/app/core/llm_factory.py
"""LLM provider factory for cloud and air-gapped deployments."""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.core.config import AgentSettings


def create_llm(agent_settings: AgentSettings) -> BaseChatModel:
    """Create an LLM instance based on the configured provider."""
    if agent_settings.llm_provider == "openrouter":
        base_url = agent_settings.llm_base_url or "https://openrouter.ai/api/v1"
        return ChatOpenAI(
            base_url=base_url,
            api_key=agent_settings.llm_api_key,
            model=agent_settings.llm_model,
            streaming=True,
        )
    elif agent_settings.llm_provider == "ollama":
        base_url = agent_settings.llm_base_url or "http://localhost:11434"
        return ChatOllama(
            base_url=base_url,
            model=agent_settings.llm_model,
        )
    raise ValueError(f"Unknown LLM provider: {agent_settings.llm_provider}")
```

- [ ] **Step 2: Create agent state schema with merge reducer**

```python
# apps/agent/app/agent/state.py
"""LangGraph agent state schema for threat analysis."""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


def update_draft(current: dict, update: dict) -> dict:
    """Merge reducer: patches only the keys provided by the tool."""
    return {**current, **update}


class AnalystAgentState(TypedDict):
    """State schema for the analyst agent graph."""
    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    session_context: dict
    report_draft: Annotated[dict, update_draft]
    tool_errors: list[str]
```

- [ ] **Step 3: Commit**

```bash
git add apps/agent/app/core/llm_factory.py apps/agent/app/agent/state.py
git commit -m "feat: add LLM provider factory and AnalystAgentState schema"
```

---

### Task 3: Agent Tools + System Prompts

**Files:**
- Create: `apps/agent/app/agent/tools.py`
- Create: `apps/agent/app/agent/prompts.py`

- [ ] **Step 1: Create agent tools**

```python
# apps/agent/app/agent/tools.py
"""LangGraph tools for the analyst agent.

Security constraint: No network tools, no DB tools, no file tools.
The agent can only reason about injected context and produce structured output.
"""

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ReportHeader(BaseModel):
    when: str = Field(description="ISO timestamp of the analysis")
    what: str = Field(description="Short summary, max 100 characters")
    who: str = Field(description="Analyst name or System")


class AssetSummaryItem(BaseModel):
    asset_value: str = Field(description="The IOC value (IP, domain, hash)")
    findings: str = Field(description="Summary of enrichment results")


class ReportBody(BaseModel):
    assets_summary: list[AssetSummaryItem] = Field(description="List of assets with findings")


class ReportFoot(BaseModel):
    conclusion: str = Field(description="Overall analysis conclusion")
    next_steps: list[str] = Field(description="Recommended next steps")
    tips_and_measures: list[str] = Field(description="Security tips and measures")


class FullReport(BaseModel):
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
    """Update a specific section of the report draft.
    Args:
        section: One of header, body, or foot
        content: The new content for that section
    """
    if section not in ("header", "body", "foot"):
        return {"error": f"Invalid section: {section}. Must be header, body, or foot."}
    return {section: content}
```

- [ ] **Step 2: Create system prompts**

```python
# apps/agent/app/agent/prompts.py
"""System prompts for the analyst agent."""

ANALYST_SYSTEM_PROMPT = """You are a senior threat intelligence analyst working in a SOC.

Your task is to analyze session data containing IOCs (Indicators of Compromise)
and their enrichment results from VirusTotal and AbuseIPDB.

## Your capabilities:
1. Analyze IOCs and their threat intelligence data
2. Generate structured threat reports using the generate_report tool
3. Update specific report sections using the update_report_section tool

## Report guidelines:
- Be concise and actionable
- Prioritize critical findings (high VT scores, high AbuseIPDB confidence)
- Note assets marked as [INTERNAL_*] - these are internal assets that were DLP-masked
- Recommend concrete next steps (block IPs, investigate hosts, update firewall rules)
- Use professional SOC language

## Important:
- Values like [INTERNAL_IP_001] are masked internal assets - reference them by their token
- Focus on external threat indicators and their risk to the organization
- If enrichment data is empty, note what additional enrichment would be valuable
"""

LAYER1_INSTRUCTION = """Analyze the complete session context and generate a structured threat report.

Steps:
1. Analyze the findings - identify critical threats, suspicious indicators, and benign results
2. Stream your analysis as markdown text (the user sees this in a chat bubble)
3. Finally, call generate_report with the structured {header, body, foot} output

Focus on: What happened? What is critical? What should the analyst do next?"""

LAYER2_INSTRUCTION = """You are in a conversation with a SOC analyst about an active analysis session.

You have access to the full session context and the current report draft.
The analyst may ask follow-up questions, request report modifications, or ask for deeper analysis.

When the analyst asks to change the report, use update_report_section to modify specific sections.
Always reference the current report draft when making changes - the analyst may have edited it manually."""
```

- [ ] **Step 3: Commit**

```bash
git add apps/agent/app/agent/tools.py apps/agent/app/agent/prompts.py
git commit -m "feat: add agent tools (generate_report, update_report_section) and system prompts"
```

---

### Task 4: LangGraph Graph + FastAPI SSE Endpoints

**Files:**
- Create: `apps/agent/app/agent/graph.py`
- Create: `apps/agent/app/router/agent.py`
- Modify: `apps/agent/app/main.py`

- [ ] **Step 1: Create graph definition** (see spec Section 5)

Create `apps/agent/app/agent/graph.py`:
- Import StateGraph, END, ToolNode from langgraph
- Create LLM via `create_llm(settings)`, bind tools
- `agent_node`: invokes llm_with_tools on messages
- `should_continue`: routes to tools if tool_calls, else END
- `process_tool_results`: extracts report_draft from tool output
- Graph: agent -> conditional(tools|END), tools -> process_results -> agent
- `build_layer1_messages(session_context)`: SystemMessage + HumanMessage
- `build_layer2_messages(context, history, draft, message)`: full message list

- [ ] **Step 2: Create FastAPI SSE endpoints** (see spec Section 6)

Create `apps/agent/app/router/agent.py`:
- AnalyzeRequest/ChatRequest Pydantic schemas
- `stream_agent_response`: async generator yielding SSE events via sse-starlette
- POST /api/agent/analyze and POST /api/agent/chat endpoints

- [ ] **Step 3: Update agent main.py** - add CORS, register router

- [ ] **Step 4: Verify** - `docker compose build ai-agent`, check health endpoint

- [ ] **Step 5: Commit**

```bash
git add apps/agent/app/agent/graph.py apps/agent/app/router/agent.py apps/agent/app/main.py
git commit -m "feat: add LangGraph graph and SSE streaming endpoints"
```

---

## Part 2: Middleware SSE Proxy + DLP Masking (Tasks 5-7)

### Task 5: DLP Masking Engine

**Files:**
- Create: `apps/middleware-api/app/services/dlp_masking.py`
- Create: `apps/middleware-api/tests/test_dlp_masking.py`

- [ ] **Step 1: Write failing tests** - 6 test cases (see plan body above for details)

- [ ] **Step 2: Run tests to verify they fail** - `python -m pytest tests/test_dlp_masking.py -v`

- [ ] **Step 3: Implement DLPMaskingContext** (see spec Section 7)

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add apps/middleware-api/app/services/dlp_masking.py apps/middleware-api/tests/test_dlp_masking.py
git commit -m "feat: add DLPMaskingContext for AI agent proxy"
```

---

### Task 6: SSE Proxy Endpoint (Layer 1 - Analyze)

**Files:**
- Create: `apps/middleware-api/app/router/agent_proxy.py`
- Modify: `apps/middleware-api/app/main.py`

- [ ] **Step 1: Create agent proxy router** (see spec Sections 6-7)

Create `apps/middleware-api/app/router/agent_proxy.py`:
- `_build_session_context(session, assets)`: builds context dict
- `_proxy_agent_stream(agent_url, payload, masking_ctx)`: SSE proxy generator
  - Level 1: buffer until SSE event boundary (double newline)
  - Level 2: buffer token events with incomplete [INTERNAL_*] tokens
  - Unmask report_draft/report_section JSON payloads directly
  - Pass through tool_call/done/error events unchanged
- GET `/{session_id}/agent/stream`: load session, mask, proxy to agent, unmask response

- [ ] **Step 2: Register router** - add to main.py imports and include_router

- [ ] **Step 3: Verify** - `docker compose build middleware-api`

- [ ] **Step 4: Commit**

```bash
git add apps/middleware-api/app/router/agent_proxy.py apps/middleware-api/app/main.py
git commit -m "feat: add SSE proxy for Layer 1 analysis with DLP unmasking"
```

---

### Task 7: Chat Proxy Endpoint (Layer 2)

**Files:**
- Modify: `apps/middleware-api/app/router/agent_proxy.py`

- [ ] **Step 1: Add ChatProxyRequest schema and POST endpoint**

Add POST `/{session_id}/agent/chat`:
- Same DLP masking flow as Layer 1
- Additionally mask report_draft and user message
- Forward to {settings.agent_url}/api/agent/chat

- [ ] **Step 2: Verify** - `docker compose build middleware-api`

- [ ] **Step 3: Commit**

```bash
git add apps/middleware-api/app/router/agent_proxy.py
git commit -m "feat: add Layer 2 chat proxy with DLP masking"
```

---

## Part 3: Frontend - Chat Panel + Report Canvas (Tasks 8-12)

### Task 8: TypeScript Types + Zustand Store Extensions

**Files:**
- Create: `apps/web-ui/src/types/agent.ts`
- Modify: `apps/web-ui/src/store/sessionStore.ts`

- [ ] **Step 1: Create agent types** (see spec Section 8)

Create `apps/web-ui/src/types/agent.ts` with:
- ChatMessage, ReportHeader, AssetSummaryItem, ReportBody, ReportFoot, ReportDraft
- AgentEventType, AgentSSEEvent, EMPTY_REPORT_DRAFT const

- [ ] **Step 2: Extend Zustand store**

Add to `sessionStore.ts`:
- New state: chatMessages, reportDraft (Record<string, T>), agentStreaming (bool)
- New actions: addChatMessage, appendToLastAssistantMessage, setReportDraft, patchReportSection, setAgentStreaming
- Keep ALL existing state and actions unchanged

- [ ] **Step 3: Commit**

```bash
git add apps/web-ui/src/types/agent.ts apps/web-ui/src/store/sessionStore.ts
git commit -m "feat: add agent types and extend Zustand store"
```

---

### Task 9: SSE Client

**Files:**
- Create: `apps/web-ui/src/api/sseClient.ts`
- Modify: `apps/web-ui/package.json` (add react-markdown)

- [ ] **Step 1: Install react-markdown** - `cd apps/web-ui && npm install react-markdown`

- [ ] **Step 2: Create SSE stream client** using native fetch + getReader()

- SSECallbacks interface: onToken, onReportDraft, onReportSection, onToolCall, onError, onDone
- consumeStream: buffer until double-newline, parse data lines, dispatch
- streamAnalysis: GET /api/sessions/{id}/agent/stream
- streamChat: POST /api/sessions/{id}/agent/chat

- [ ] **Step 3: Commit**

```bash
git add apps/web-ui/src/api/sseClient.ts apps/web-ui/package.json apps/web-ui/package-lock.json
git commit -m "feat: add SSE stream client for AI agent"
```

---

### Task 10: ChatPanel + ChatMessage Components

**Files:**
- Create: `apps/web-ui/src/components/ChatMessage.tsx`
- Create: `apps/web-ui/src/components/ChatPanel.tsx`
- Modify: `apps/web-ui/src/layout/CenterPanel.tsx`

- [ ] **Step 1: Create ChatMessage** - user=right/primary, assistant=left/muted with ReactMarkdown

- [ ] **Step 2: Create ChatPanel** - message list + textarea input + Send button

Uses streamChat, Zustand chat actions, AbortController. Enter sends, Shift+Enter newline.

- [ ] **Step 3: Update CenterPanel** - replace placeholder with UploadZone (shrink-0) + ChatPanel (flex-1)

- [ ] **Step 4: Commit**

```bash
git add apps/web-ui/src/components/ChatMessage.tsx apps/web-ui/src/components/ChatPanel.tsx apps/web-ui/src/layout/CenterPanel.tsx
git commit -m "feat: add ChatPanel and ChatMessage, replace center placeholder"
```

---

### Task 11: Report Canvas Component

**Files:**
- Create: `apps/web-ui/src/components/ReportCanvas.tsx`

- [ ] **Step 1: Create ReportCanvas** (see spec Section 8)

Three editable sections from ReportDraft:
- **Header**: inline fields for what, when, who
- **Body**: assets_summary rows with asset_value (mono) + editable findings
- **Foot**: conclusion textarea + next_steps/tips_and_measures (one per line)
- Empty state: dashed border placeholder
- All edits call patchReportSection -> agent sees manual changes on next chat

- [ ] **Step 2: Commit**

```bash
git add apps/web-ui/src/components/ReportCanvas.tsx
git commit -m "feat: add ReportCanvas with editable sections"
```

---

### Task 12: AnalyzeButton + RightPanel Wiring

**Files:**
- Create: `apps/web-ui/src/components/AnalyzeButton.tsx`
- Modify: `apps/web-ui/src/layout/RightPanel.tsx`

- [ ] **Step 1: Create AnalyzeButton** - triggers Layer 1 via streamAnalysis, same SSE pattern as ChatPanel

- [ ] **Step 2: Update RightPanel** - header bar with AnalyzeButton, enable Report tab, add ReportCanvas

- [ ] **Step 3: Verify frontend builds** - `cd apps/web-ui && npm run build`

- [ ] **Step 4: Commit**

```bash
git add apps/web-ui/src/components/AnalyzeButton.tsx apps/web-ui/src/layout/RightPanel.tsx
git commit -m "feat: add AnalyzeButton, wire ReportCanvas, enable Report tab"
```

---

## Integration Test (Task 13)

### Task 13: Full Stack E2E Verification

**Files:** No new files - verification task.

- [ ] **Step 1: Build all** - `docker compose up -d --build`

- [ ] **Step 2: Verify agent health** - `curl http://localhost:8001/api/health`

- [ ] **Step 3: Create session + upload IOCs** (8.8.8.8, 1.1.1.1, example.com, 192.168.1.10)

- [ ] **Step 4: Test Layer 1** - `curl -N .../agent/stream` - expect SSE token/report_draft/done events

- [ ] **Step 5: Test Layer 2** - POST to /agent/chat with a message

- [ ] **Step 6: Verify DLP masking** - agent logs should show [INTERNAL_IP_001], never real IPs

- [ ] **Step 7: Open UI** - verify ChatPanel, Report tab, Analyze button all work

- [ ] **Step 8: Commit any fixes**

```bash
git add -A
git commit -m "fix: E2E integration fixes for Phase 3"
```