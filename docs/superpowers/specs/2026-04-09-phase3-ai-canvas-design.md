# Phase 3: AI Agent + Report Canvas — Design Specification

**Date:** 2026-04-09
**Status:** Approved
**Depends on:** Phase 1 (Foundation), Phase 2A (DLP), Phase 2B (n8n Enrichment)

---

## 1. Goal

Transform SECCENTER from a data aggregator into an AI-powered Cyber Security Cockpit. An analyst uploads IOCs, the pipeline enriches them, and the LangGraph agent instantly synthesizes a structured threat report — reducing Mean Time To Understand (MTTU) from 30 minutes to 30 seconds.

Phase 3 delivers two paired features: (1) a LangGraph AI agent for automated analysis and conversational refinement, and (2) a Report Canvas for structured, editable output. The AI needs a place to write; the analyst needs a place to edit.

---

## 2. Interaction Model

### Layer 1 — Automated Report Generation (zero-prompt)

The analyst clicks "Analyze Session". The agent reads the full session context (assets, enrichment data, statuses), generates a structured threat summary, and streams it into the Report Canvas as a markdown draft. No prompting required. Covers 80% of the use case.

**Flow:**
1. Analyst clicks "Analyze Session" button
2. Middleware builds DLPMaskingContext, masks internal asset values
3. Middleware sends masked session context to ai-agent container
4. Agent streams markdown analysis (chat bubble typing effect)
5. Agent finalizes structured `{header, body, foot}` report
6. Middleware unmasks tokens in SSE stream
7. Frontend populates Report Canvas, auto-switches to Canvas tab

**UX refinement:** The agent streams pure markdown text first (visible in chat bubble), then executes the `generate_report` tool to produce the structured `{header, body, foot}` payload. This two-phase approach ensures smooth streaming UX regardless of LLM provider structured output limitations.

### Layer 2 — Conversational Refinement (high ceiling)

The analyst reads the draft and asks follow-up questions in the Chat panel: "Are these two C2 IPs from the same campaign?", "Write an executive summary for the CISO", "Which internal assets should we isolate first?"

Each response can update specific report sections via `update_report_section` tool calls. The agent always has access to the current `reportDraft` (including analyst manual edits) and the full session context.

**Key insight:** The Chat and Canvas share the same session context. The agent never asks the analyst to paste IOCs — it continuously pulls the live session state.

---

## 3. Container Architecture

### New: `ai-agent` container

- Python service running LangGraph with FastAPI
- Exposes REST API for middleware to call (not directly accessible from frontend)
- Stateless — session context injected per-request by middleware
- Env-driven LLM routing via factory pattern
- Dependencies: `langgraph`, `langchain-core`, `langchain-openai`, `langchain-ollama`, `fastapi`, `uvicorn`

### Modified: `middleware-api`

- New SSE proxy endpoint: `GET /api/sessions/{id}/agent/stream` (Layer 1)
- New chat proxy endpoint: `POST /api/sessions/{id}/agent/chat` (Layer 2)
- New service: `DLPMaskingContext` for ephemeral mask map construction
- Stream-to-stream proxying: `httpx.AsyncClient.stream()` into `FastAPI.StreamingResponse` with per-chunk unmasking

### Modified: `web-ui`

- Middle column: ChatPanel component with SSE streaming
- Right column: New "Report Canvas" tab alongside Asset Control Center
- "Analyze Session" button in right column header

**Why a separate ai-agent container?**
- **Dependency isolation:** LangGraph/LangChain ecosystem is heavy. Keeps middleware lean and fast.
- **Long-running requests:** Agent calls take 10-30s. Separate container prevents event-loop starvation in the middleware.
- **Architecture alignment:** Matches the original container topology from `docs/architecture.md`.

---

## 4. LLM Provider Routing

Environment-driven abstraction ensuring deployment in both cloud-connected and air-gapped environments.

### Configuration (env vars on ai-agent container)

| Variable | Values | Default |
|----------|--------|---------|
| `LLM_PROVIDER` | `openrouter`, `ollama` | `openrouter` |
| `LLM_MODEL` | Any model string | `anthropic/claude-sonnet-4-20250514` |
| `LLM_API_KEY` | API key (openrouter only) | — |
| `LLM_BASE_URL` | Override base URL | Provider default |

### Factory Pattern

```python
def create_llm(settings: AgentSettings) -> BaseChatModel:
    if settings.llm_provider == "openrouter":
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    elif settings.llm_provider == "ollama":
        return ChatOllama(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

Uses LangChain's `BaseChatModel` abstraction. Both providers support streaming and structured output via the same interface. The `{header, body, foot}` schema is enforced via `model.with_structured_output()`.

---

## 5. LangGraph Agent

### State Schema

```python
class AnalystAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    session_context: dict           # Injected by middleware (pre-masked)
    report_draft: Annotated[dict[str, str], update_draft]  # {header, body, foot}
    tool_errors: list[str]          # Self-correction loop
```

**Critical design choice:** `session_context` is injected by the middleware on every request, not fetched by the agent. The agent has no DB access and never sees raw internal asset values.

### State Reducer for report_draft

```python
def update_draft(current: dict, update: dict) -> dict:
    """Merge reducer: patches only the keys provided by the tool."""
    return {**current, **update}
```

This prevents `update_report_section` tool calls from overwriting the entire draft when only one section changes.

### Agent Tools

| Tool | Purpose | I/O |
|------|---------|-----|
| `read_session_context` | Returns injected `session_context` from state | Pure state read, no network |
| `generate_report` | Structures LLM output into `{header, body, foot}` | Uses structured output |
| `update_report_section` | Replaces a specific section (header/body/foot) | Returns partial dict for merge reducer |

**Security constraint:** The agent has no network tools, no DB tools, no file tools. It can only reason about the context it was given and produce structured output. Maximum security, minimum attack surface.

### Output Schema (from docs/output-shemata.md)

```json
{
  "header": {
    "when": "ISO timestamp",
    "what": "Short summary (max 100 chars)",
    "who": "Analyst name or 'System'"
  },
  "body": {
    "assets_summary": [
      { "asset_value": "8.8.8.8", "findings": "VT clean, AbuseIPDB score 5" }
    ]
  },
  "foot": {
    "conclusion": "Analysis conclusion",
    "next_steps": ["Step 1", "Step 2"],
    "tips_and_measures": ["Tip 1", "Tip 2"]
  }
}
```

---

## 6. API Contracts

### Middleware to AI Agent (internal network only)

**POST /api/agent/analyze (SSE stream)**

Request:
```json
{
  "session_id": "01KNQ...",
  "messages": [],
  "session_context": {
    "assets": [
      {"id": "...", "value": "8.8.8.8", "type": "IP_ADDRESS", "status": "ENRICHED",
       "enrichment_data": {"vt_score": 0}},
      {"id": "...", "value": "[INTERNAL_IP_001]", "type": "IP_ADDRESS", "status": "INTERNAL",
       "enrichment_data": {}}
    ],
    "session_name": "Incident 2026-04-09"
  },
  "report_draft": {"header": {}, "body": {}, "foot": {}}
}
```

**POST /api/agent/chat (SSE stream)**

Same schema, but `messages` contains conversation history and `report_draft` contains the current (possibly analyst-edited) canvas state.

### SSE Event Types

| Type | Purpose | Frontend Action |
|------|---------|-----------------|
| `token` | Streaming text chunk | Append to chat bubble |
| `report_draft` | Complete structured report | Replace Canvas content |
| `report_section` | Single section update | Patch specific Canvas section |
| `tool_call` | Agent calling a tool | Show "thinking" indicator |
| `error` | Agent error | Display error toast |
| `done` | Stream complete | Stop loading state |

### Frontend to Middleware

**GET /api/sessions/{id}/agent/stream** — Layer 1 (no body needed, session context loaded server-side)

**POST /api/sessions/{id}/agent/chat** — Layer 2
```json
{
  "message": "Make the executive summary shorter",
  "report_draft": { "header": {}, "body": {}, "foot": {} }
}
```

---

## 7. DLP Masking Boundary

### The Mask/Unmask Sandwich

```
Frontend          Middleware               AI Agent
--------         -----------              ---------

[Analyze] --> 1. Load session assets
              2. Build DLPMaskingContext
              3. Mask internal values
              4. Inject masked context --> Receives only masked data
                                           LLM sees [INTERNAL_IP_001]
                                           Streams response with tokens
              5. Consume SSE stream  <--  SSE chunks
              6. Content-aware unmask
              7. Forward to browser
 <-- 8. Analyst sees real values
```

### DLPMaskingContext Implementation

```python
class DLPMaskingContext:
    """Session-scoped, ephemeral mask map. Never persisted."""

    def __init__(self, assets: list[AssetModel]):
        self._map: dict[str, str] = {}       # token -> real value
        self._reverse: dict[str, str] = {}    # real value -> token
        counters: dict[str, int] = {}

        for asset in assets:
            if asset.status != "INTERNAL":
                continue
            asset_type = asset.type.split("_")[0]  # IP, DOMAIN, FILE
            counters[asset_type] = counters.get(asset_type, 0) + 1
            token = f"[INTERNAL_{asset_type}_{counters[asset_type]:03d}]"
            self._map[token] = asset.value
            self._reverse[asset.value] = token

    def mask(self, text: str) -> str:
        for real_value, token in self._reverse.items():
            text = text.replace(real_value, token)
        return text

    def unmask(self, text: str) -> str:
        for token, real_value in self._map.items():
            text = text.replace(token, real_value)
        return text
```

### Token Properties

- **Deterministic:** Same asset always maps to the same token within a session
- **Positionally stable:** Consistent across multi-turn conversations
- **Distinctive format:** `[INTERNAL_TYPE_NNN]` — parseable, human-readable for LLM reasoning
- **Ephemeral:** Map constructed per-request from live asset table, never persisted

### SSE Proxy with Content-Aware Unmasking

The middleware proxy handles two levels of chunking:

**Level 1 — SSE event boundaries:** Buffer until complete `\n\n`-delimited events arrive. Prevents network-level chunk splits.

**Level 2 — LLM tokenization splits:** The LLM tokenizer may split `[INTERNAL_IP_001]` across multiple `token` events (e.g., `[`, `INTERNAL`, `_IP_001]`). The proxy implements a content-level token buffer:

- When a `token` event's content contains `[` but no closing `]`, hold it in a buffer
- Accumulate subsequent `token` events into the buffer
- When `]` arrives, run `unmask()` on the accumulated buffer and yield as a single event
- For `report_draft` and `report_section` events (complete JSON payloads), unmask directly

### Three Hard Guarantees

1. Internal asset values **never reach the LLM provider**
2. The mask map **never reaches the browser**
3. The analyst **never sees masked tokens**

---

## 8. Frontend Architecture

### Layout

```
+------------------+------------------+---------------------------+
|  Left Column     |  Middle Column   |  Right Column (Tabs)      |
|  (Navigation)    |  (Chat Panel)    |  [Assets] [Report Canvas] |
|                  |                  |                           |
|  Session list    |  Chat messages   |  Tab content:             |
|  Session history |  Streaming AI    |  - AssetTable (existing)  |
|                  |  responses       |  - ReportCanvas (new)     |
|                  |                  |                           |
|                  |  [Input box]     |  [Analyze Session] button |
+------------------+------------------+---------------------------+
```

### New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ChatPanel` | Middle column | Message list + input, SSE stream consumer |
| `ChatMessage` | Inside ChatPanel | Single message bubble with streaming support |
| `ReportCanvas` | Right column tab 2 | Editable markdown sections for {header, body, foot} |
| `AnalyzeButton` | Right column header | Triggers Layer 1 automated report |

### Zustand Store Extensions

```typescript
interface SessionState {
  // ... existing fields ...

  /** Chat messages per session */
  chatMessages: Record<string, ChatMessage[]>;
  /** Report draft per session */
  reportDraft: Record<string, ReportDraft>;
  /** Whether the agent is currently streaming */
  agentStreaming: boolean;

  addChatMessage: (sessionId: string, message: ChatMessage) => void;
  setReportDraft: (sessionId: string, draft: ReportDraft) => void;
  patchReportSection: (sessionId: string, section: string, content: string) => void;
  setAgentStreaming: (streaming: boolean) => void;
}
```

### TypeScript Types

```typescript
interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface ReportDraft {
  header: { when: string; what: string; who: string };
  body: { assets_summary: Array<{ asset_value: string; findings: string }> };
  foot: { conclusion: string; next_steps: string[]; tips_and_measures: string[] };
}
```

### SSE Consumer

The frontend uses `fetch` with `response.body.getReader()` or the `@microsoft/fetch-event-source` library (not native `EventSource`) because Layer 2 requires POST requests with JSON bodies, which the native EventSource API does not support.

The consumer dispatches events to the Zustand store via a switch on `data.type`:
- `token` — accumulate content on the same `messageId` (smooth typing animation)
- `report_draft` — `setReportDraft()` (full Canvas replacement)
- `report_section` — `patchReportSection()` (surgical Canvas update)
- `done` — `setAgentStreaming(false)`, close stream
- `error` — display error toast, close stream

### Report Canvas

Renders `ReportDraft` as three editable sections:
- **Header:** Metadata bar (when, what, who) — inline editable fields
- **Body:** Assets summary table, each row editable
- **Foot:** Conclusion paragraph + bulleted next_steps and tips_and_measures

Analyst edits update the Zustand store via `patchReportSection`. When the analyst then chats with the agent, the current (edited) `reportDraft` is sent — the agent sees manual changes.

Implementation: `react-markdown` for rendering, plain `textarea` for editing. No rich editor library in Phase 3.

---

## 9. Docker Infrastructure

### New ai-agent service in docker-compose.yml

```yaml
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

### Middleware env additions

```yaml
- SECCENTER_AGENT_URL=http://ai-agent:8001
```

### Directory structure

```
apps/agent/
  Dockerfile
  requirements.txt
  app/
    main.py              # FastAPI entry point
    core/
      config.py          # AgentSettings (LLM provider config)
      llm_factory.py     # create_llm() factory
    agent/
      state.py           # AnalystAgentState TypedDict
      graph.py           # LangGraph graph definition
      tools.py           # read_session_context, generate_report, update_report_section
      prompts.py         # System prompts for analysis
    router/
      agent.py           # POST /api/agent/analyze, POST /api/agent/chat
```

---

## 10. YAGNI Boundaries (Not in Phase 3)

- No rich Markdown editor (react-markdown + textarea, upgrade later)
- No report export/PDF (copy-paste from Canvas)
- No chat history persistence to DB (session-scoped in Zustand, lost on reload)
- No WebSocket upgrade (SSE via fetch is sufficient)
- No multi-session agent memory (agent context is per-request)
- No RAG / "Chat with Data" (requires pgvector setup, deferred to Phase 4)
- No FalkorDB graph queries (deferred to Phase 4+)

---

## 11. Security Summary

| Boundary | Enforcement |
|----------|-------------|
| Internal assets never reach LLM | DLPMaskingContext masks before injection |
| Mask map never reaches browser | Server-side unmasking in SSE proxy |
| Agent has no DB/network access | No tools with I/O, context is injected |
| LLM API keys isolated | Only in ai-agent container env |
| Agent container has no DLP rules | Middleware is sole DLP gatekeeper |
| Tokenization leaks prevented | Content-level token buffering in SSE proxy |
