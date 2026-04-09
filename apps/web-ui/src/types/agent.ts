/**
 * TypeScript types for AI agent chat and report canvas
 */

/** Single chat message in the AI conversation */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

/** Report header metadata */
export interface ReportHeader {
  when: string;
  what: string;
  who: string;
}

/** Single asset finding in report body */
export interface AssetSummaryItem {
  asset_value: string;
  findings: string;
}

/** Report body section */
export interface ReportBody {
  assets_summary: AssetSummaryItem[];
}

/** Report foot section */
export interface ReportFoot {
  conclusion: string;
  next_steps: string[];
  tips_and_measures: string[];
}

/** Complete structured report draft */
export interface ReportDraft {
  header: ReportHeader;
  body: ReportBody;
  foot: ReportFoot;
}

/** SSE event types from the agent proxy */
export type AgentEventType =
  | "token"
  | "report_draft"
  | "report_section"
  | "tool_call"
  | "error"
  | "done";

/** Parsed SSE event from agent stream */
export interface AgentSSEEvent {
  event: AgentEventType;
  data: Record<string, unknown>;
}

/** Empty report draft constant for initialization */
export const EMPTY_REPORT_DRAFT: ReportDraft = {
  header: { when: "", what: "", who: "" },
  body: { assets_summary: [] },
  foot: { conclusion: "", next_steps: [], tips_and_measures: [] },
};
