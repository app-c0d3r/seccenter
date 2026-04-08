/**
 * Upload-Zone: Drag-and-Drop und Klick-Upload fuer IOC-Extraktion
 * Unterstuetzt TXT, CSV, LOG und PDF Dateien bis 10 MB
 */
import { useRef, useState } from "react";
import { useSessionStore } from "@/store/sessionStore";
import { apiClient } from "@/api/apiClient";
import { cn } from "@/lib/utils";

/** Maximale Dateigroesse in Bytes (10 MB) */
const MAX_FILE_SIZE = 10 * 1024 * 1024;

/** Erlaubte MIME-Typen fuer den Upload */
const ACCEPTED_TYPES = [
  "text/plain",
  "text/csv",
  "application/pdf",
];

/** Upload-Bereich mit Drag-and-Drop Unterstuetzung */
export function UploadZone() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { activeSessionId, addAssetsToSession } = useSessionStore((state) => ({
    activeSessionId: state.activeSessionId,
    addAssetsToSession: state.addAssetsToSession,
  }));

  /** Validiert die Datei auf Typ und Groesse */
  function validateFile(file: File): string | null {
    const erlaubteEndungen = [".txt", ".csv", ".log", ".pdf"];
    const dateiendung = file.name.toLowerCase().slice(file.name.lastIndexOf("."));

    if (!erlaubteEndungen.includes(dateiendung) && !ACCEPTED_TYPES.includes(file.type)) {
      return "Nicht unterstuetzter Dateityp. Erlaubt: TXT, CSV, LOG, PDF.";
    }
    if (file.size > MAX_FILE_SIZE) {
      return "Datei zu gross. Maximale Groesse: 10 MB.";
    }
    return null;
  }

  /** Verarbeitet eine ausgewaehlte Datei und laedt sie hoch */
  async function handleFile(file: File) {
    if (!activeSessionId) {
      setErrorMessage("Keine aktive Session. Bitte zuerst eine Session erstellen.");
      return;
    }

    const validierungsFehler = validateFile(file);
    if (validierungsFehler) {
      setErrorMessage(validierungsFehler);
      return;
    }

    setErrorMessage(null);
    setIsUploading(true);

    try {
      const result = await apiClient.uploadFile(activeSessionId, file);
      addAssetsToSession(activeSessionId, result.assets);
    } catch (error: unknown) {
      console.error("Datei-Upload fehlgeschlagen:", error);
      setErrorMessage("Upload fehlgeschlagen. Bitte erneut versuchen.");
    } finally {
      setIsUploading(false);
    }
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) {
      void handleFile(file);
    }
  }

  function handleInputChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      void handleFile(file);
    }
    // Eingabe zuruecksetzen fuer erneuten Upload derselben Datei
    event.target.value = "";
  }

  function handleClick() {
    fileInputRef.current?.click();
  }

  return (
    <div className="w-full">
      {/* Verstecktes Datei-Input-Element */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.csv,.log,.pdf"
        className="hidden"
        onChange={handleInputChange}
      />

      {/* Drag-and-Drop Zone */}
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/30 hover:border-muted-foreground/50 hover:bg-muted/30",
          isUploading && "pointer-events-none opacity-60"
        )}
      >
        {isUploading ? (
          <p className="text-sm font-medium text-muted-foreground">Extracting IOCs...</p>
        ) : (
          <>
            <p className="text-sm font-medium">Drop file here or click to upload</p>
            <p className="mt-1 text-xs text-muted-foreground">TXT, CSV, PDF — max 10 MB</p>
          </>
        )}
      </div>

      {/* Fehlermeldung */}
      {errorMessage && (
        <p className="mt-2 text-xs text-destructive">{errorMessage}</p>
      )}
    </div>
  );
}
