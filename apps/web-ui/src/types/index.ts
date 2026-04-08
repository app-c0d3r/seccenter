/**
 * Zentrale TypeScript-Typdefinitionen fuer SECCENTER
 * Definiert alle Kern-Datenstrukturen fuer Assets und Analyse-Sessions
 */

/** Moegliche Typen eines analysierten Assets */
export type AssetType =
  | "IP_ADDRESS"
  | "DOMAIN"
  | "FILE_HASH_MD5"
  | "FILE_HASH_SHA1"
  | "FILE_HASH_SHA256";

/** Status eines analysierten Assets im Workflow */
export type AssetStatus =
  | "PENDING"
  | "INTERNAL"
  | "PROCESSING"
  | "ENRICHED"
  | "CRITICAL"
  | "CONFIRMED"
  | "IGNORED";

/** Ein einzelnes analysiertes Asset (IOC) */
export interface AnalyzedAsset {
  id: string;
  session_id: string;
  value: string;
  type: AssetType;
  status: AssetStatus;
  created_at: string;
  enrichment_data: Record<string, unknown>;
}

/** Eine Analyse-Session, die mehrere Assets enthalten kann */
export interface AnalysisSession {
  id: string;
  name: string;
  assets: AnalyzedAsset[];
  created_at: string;
}
