### Das Asset-Datenmodell (TypeScript Interfaces)

Wenn ein Analyst eine CSV oder PDF hochlädt, extrahiert das Backend die Daten und schickt sie als Array dieses Objekttyps an die React-UI:

```json
// Enum für den aktuellen Bearbeitungsstatus in der UI
export enum AssetStatus {
  PENDING = 'PENDING',       // 🟡 Neu extrahiert, noch nichts passiert
  PROCESSING = 'PROCESSING', // ⏳ n8n arbeitet gerade daran (Batching/Pacing)
  ENRICHED = 'ENRICHED',     // 🟢 n8n ist fertig, Daten liegen vor
  INTERNAL = 'INTERNAL',     // 🛡️ Durch Middleware als intern markiert (DLP)
  CRITICAL = 'CRITICAL',     // 🔴 n8n meldet Bedrohung (z.B. VirusTotal Score > 0)
}

// Enum für die Asset-Klassifizierung
export enum AssetType {
  IP_ADDRESS = 'IP_ADDRESS',
  DOMAIN = 'DOMAIN',
  URL = 'URL',
  FILE_HASH = 'FILE_HASH',
  EMAIL = 'EMAIL',
  PERSON = 'PERSON',
}

// Das Kern-Objekt für die Staging-Tabelle im UI
export interface AnalyzedAsset {
  id: string;                // UUID / ULID für React-Keys
  value: string;             // z.B. "1.2.3.4" oder "evil.com"
  type: AssetType;
  status: AssetStatus;
  
  // Metadaten für die UI-Anzeige
  sourceFile?: string;       // Aus welcher Datei stammt es? (z.B. "malware_report.pdf")
  extractedAt: string;       // ISO-Timestamp
  
  // Die tatsächlichen Enrichment-Daten (werden asynchron via WebSocket befüllt)
  enrichmentData?: Record<string, any>; // z.B. VirusTotal JSON-Response
  
  // UI-State (wird nicht in der DB gespeichert, nur für das aktuelle Handling)
  isSelected: boolean;       // Hat der Analyst die Checkbox in der Tabelle aktiviert?
}
```

### 2. Das Session-Modell (Für die Tabs / Workspaces)

Um deine Anforderung der parallelen Bearbeitung (Multitasking) zu erfüllen, kapseln wir diese Assets in einer Session:

```json
export interface AnalysisSession {
  sessionId: string;                 // UUID / ULID (Das ist die ID in der URL zum Teilen)
  title: string;                     // z.B. "Analyse: Phishing PDF"
  createdAt: string;                 
  
  // Der Inhalt der 3 Spalten für DIESEN Tab
  chatHistory: ChatMessage[];        // Die mittlere Spalte (Chat)
  stagedAssets: AnalyzedAsset[];     // Die rechte Spalte (Tab 1: Asset-Tabelle)
  canvasContent: string;             // Die rechte Spalte (Tab 2: Editierbarer Report im Markdown)
  
  isSavedToDatabase: boolean;        // Wurde der "Speichern & Abschließen"-Button gedrückt?
}
```

### Warum dieser Aufbau so wertvoll ist

- **Eindeutige Wahrheit (Single Source of Truth):** Wenn über WebSockets ein Update von n8n reinkommt ("VirusTotal ist fertig mit IP 1.2.3.4"), sucht unser Zustand-Store einfach in `stagedAssets` nach der entsprechenden ID und ändert den `status` auf `ENRICHED`. Das UI aktualisiert sich in Echtzeit.
- **Checkbox-Aktionen (Bulk):** Durch das Feld `isSelected` kann der Analyst 10 Assets markieren und mit einem Klick auf einen Button "Ausgewählte Assets analysieren" einen gezielten Batch-Job an n8n senden.