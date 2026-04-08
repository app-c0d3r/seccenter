/**
 * Zustand-Store fuer Session- und Asset-Verwaltung
 * Nutzt Immer-Middleware fuer direkte (mutable) State-Mutationen
 */
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { AnalysisSession, AnalyzedAsset, AssetStatus } from "@/types";

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
  updateAssetStatus: (sessionId: string, assetId: string, status: AssetStatus) => void;
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
  }))
);
