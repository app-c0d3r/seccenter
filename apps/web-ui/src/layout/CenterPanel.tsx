/**
 * Mittleres Panel: Datei-Upload und AI-Chat Platzhalter
 */
import { UploadZone } from "@/components/UploadZone";

/** Mittleres Panel mit Upload-Bereich und Chat-Platzhalter */
export function CenterPanel() {
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      {/* Datei-Upload-Bereich */}
      <UploadZone />

      {/* AI-Chat Platzhalter fuer Phase 2 */}
      <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-muted-foreground/30 p-8">
        <p className="text-sm text-muted-foreground">AI Chat — Phase 2</p>
      </div>
    </div>
  );
}
