/**
 * Zustand-Store fuer Session- und Asset-Verwaltung
 * Nutzt Immer-Middleware fuer direkte (mutable) State-Mutationen
 */
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { AnalysisSession, AnalyzedAsset, AssetStatus } from "@/types";
import type { ChatMessage, ReportDraft } from "@/types/agent";
import { EMPTY_REPORT_DRAFT } from "@/types/agent";

/** Zustand-Interface des Session-Stores */
interface SessionState {
  /** ID der aktuell aktiven Session */
  activeSessionId: string | null;
  /** Alle bekannten Sessions als Dictionary (id → Session) */
  sessions: Record<string, AnalysisSession>;
  /** Setzt die aktive Session anhand der ID */
  setActiveSession: (id: string) => void;
  /** Fuegt eine neue Session zum Store hinzu */
  addSession: (session: AnalysisSession) => void;
  /** Fuegt Assets zu einer bestehenden Session hinzu */
  addAssetsToSession: (sessionId: string, assets: AnalyzedAsset[]) => void;
  /** Aktualisiert den Status eines einzelnen Assets */
  updateAssetStatus: (
    sessionId: string,
    assetId: string,
    status: AssetStatus,
  ) => void;
  /** Mark assets as PROCESSING after successful enrich dispatch */
  markAssetsProcessing: (sessionId: string, assetIds: string[]) => void;
  /** Replace all assets for a session (polling sync from backend) */
  refreshSessionAssets: (sessionId: string, assets: AnalyzedAsset[]) => void;

  /** Chat messages per session */
  chatMessages: Record<string, ChatMessage[]>;
  /** Report draft per session */
  reportDraft: Record<string, ReportDraft>;
  /** Whether the agent is currently streaming */
  agentStreaming: boolean;

  /** Add a chat message to a session */
  addChatMessage: (sessionId: string, message: ChatMessage) => void;
  /** Append content to the last assistant message (for streaming tokens) */
  appendToLastAssistantMessage: (sessionId: string, content: string) => void;
  /** Set the full report draft for a session */
  setReportDraft: (sessionId: string, draft: ReportDraft) => void;
  /** Patch a single report section */
  patchReportSection: (
    sessionId: string,
    section: string,
    content: Record<string, unknown>,
  ) => void;
  /** Set the agent streaming state */
  setAgentStreaming: (streaming: boolean) => void;
}

/** Globaler Zustand-Store fuer Sessions */
export const useSessionStore = create<SessionState>()(
  immer((set) => ({
    activeSessionId: null,
    sessions: {},

    setActiveSession: (id) =>
      set((state) => {
        state.activeSessionId = id;
      }),

    addSession: (session) =>
      set((state) => {
        state.sessions[session.id] = session;
      }),

    addAssetsToSession: (sessionId, assets) =>
      set((state) => {
        const session = state.sessions[sessionId];
        if (session) {
          session.assets.push(...assets);
        }
      }),

    updateAssetStatus: (sessionId, assetId, status) =>
      set((state) => {
        const session = state.sessions[sessionId];
        if (session) {
          const asset = session.assets.find((a) => a.id === assetId);
          if (asset) {
            asset.status = status;
          }
        }
      }),

    markAssetsProcessing: (sessionId, assetIds) =>
      set((state) => {
        const session = state.sessions[sessionId];
        if (session) {
          for (const asset of session.assets) {
            if (assetIds.includes(asset.id)) {
              asset.status = "PROCESSING";
            }
          }
        }
      }),

    refreshSessionAssets: (sessionId, assets) =>
      set((state) => {
        const session = state.sessions[sessionId];
        if (session) {
          session.assets = assets;
        }
      }),

    chatMessages: {},
    reportDraft: {},
    agentStreaming: false,

    addChatMessage: (sessionId, message) =>
      set((state) => {
        if (!state.chatMessages[sessionId]) {
          state.chatMessages[sessionId] = [];
        }
        state.chatMessages[sessionId].push(message);
      }),

    appendToLastAssistantMessage: (sessionId, content) =>
      set((state) => {
        const messages = state.chatMessages[sessionId];
        if (messages && messages.length > 0) {
          const last = messages[messages.length - 1];
          if (last.role === "assistant") {
            last.content += content;
          }
        }
      }),

    setReportDraft: (sessionId, draft) =>
      set((state) => {
        state.reportDraft[sessionId] = draft;
      }),

    patchReportSection: (sessionId, section, content) =>
      set((state) => {
        if (!state.reportDraft[sessionId]) {
          state.reportDraft[sessionId] = { ...EMPTY_REPORT_DRAFT };
        }
        (state.reportDraft[sessionId] as Record<string, unknown>)[section] =
          content;
      }),

    setAgentStreaming: (streaming) =>
      set((state) => {
        state.agentStreaming = streaming;
      }),
  })),
);
