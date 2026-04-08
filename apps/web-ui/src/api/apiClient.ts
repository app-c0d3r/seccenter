/**
 * Zentraler API-Client fuer die SECCENTER Backend-Kommunikation
 * Kapselt alle HTTP-Anfragen an das Backend via /api Endpunkt
 */
import type { AnalysisSession, AnalyzedAsset, AssetStatus } from "@/types";

/** Basis-URL fuer alle API-Anfragen */
const BASE_URL = "/api";

/**
 * Hilfsfunktion fuer JSON-Anfragen mit Fehlerbehandlung
 */
async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, options);
  if (!response.ok) {
    throw new Error(`API-Fehler ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

/**
 * Erstellt eine neue Analyse-Session
 */
export async function createSession(name: string): Promise<AnalysisSession> {
  return fetchJson<AnalysisSession>("/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

/**
 * Ruft alle vorhandenen Analyse-Sessions ab
 */
export async function listSessions(): Promise<AnalysisSession[]> {
  return fetchJson<AnalysisSession[]>("/sessions");
}

/**
 * Laedt eine Datei in eine Session hoch und extrahiert IOCs
 * Hinweis: Kein Content-Type Header – wird vom Browser automatisch gesetzt (multipart)
 */
export async function uploadFile(
  sessionId: string,
  file: File,
): Promise<{ assets: AnalyzedAsset[] }> {
  const formData = new FormData();
  formData.append("file", file);
  return fetchJson<{ assets: AnalyzedAsset[] }>(
    `/sessions/${sessionId}/upload`,
    {
      method: "POST",
      body: formData,
    },
  );
}

/**
 * Aktualisiert den Status eines Assets in einer Session
 */
export async function updateAssetStatus(
  sessionId: string,
  assetId: string,
  status: AssetStatus,
): Promise<AnalyzedAsset> {
  return fetchJson<AnalyzedAsset>(`/sessions/${sessionId}/assets/${assetId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

/**
 * Dispatches selected assets for enrichment via n8n
 */
export async function enrichAssets(
  sessionId: string,
  assetIds: string[],
): Promise<{ batch_id: string; asset_count: number }> {
  return fetchJson<{ batch_id: string; asset_count: number }>(
    `/sessions/${sessionId}/enrich`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_ids: assetIds }),
    },
  );
}

/**
 * Fetches a single session with all its assets (used for polling)
 */
export async function getSession(sessionId: string): Promise<AnalysisSession> {
  return fetchJson<AnalysisSession>(`/sessions/${sessionId}`);
}

/** Gebundeler API-Client als Objekt fuer einfachen Import */
export const apiClient = {
  createSession,
  listSessions,
  uploadFile,
  updateAssetStatus,
  enrichAssets,
  getSession,
};
