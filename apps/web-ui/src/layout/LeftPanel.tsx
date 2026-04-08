/**
 * Linkes Panel: Session-Liste mit Navigation und Erstellung neuer Sessions
 */
import { useNavigate } from "react-router-dom";
import { useSessionStore } from "@/store/sessionStore";
import { apiClient } from "@/api/apiClient";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Linkes Seiten-Panel mit Session-Liste und Neu-Session-Schaltflaeche */
export function LeftPanel() {
  const navigate = useNavigate();
  const { sessions, activeSessionId, addSession } = useSessionStore((state) => ({
    sessions: state.sessions,
    activeSessionId: state.activeSessionId,
    addSession: state.addSession,
  }));

  // Sessions nach Erstellungsdatum absteigend sortieren
  const sortedSessions = Object.values(sessions).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  /** Neue Session anlegen und dorthin navigieren */
  async function handleNewSession() {
    try {
      const session = await apiClient.createSession("New Analysis");
      addSession(session);
      navigate(`/sessions/${session.id}`);
    } catch (error: unknown) {
      console.error("Neue Session konnte nicht erstellt werden:", error);
    }
  }

  return (
    <div className="flex h-full flex-col border-r bg-background">
      {/* Kopfzeile mit Titel und Neu-Schaltflaeche */}
      <div className="border-b p-3">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Sessions
        </h2>
        <Button size="sm" className="w-full" onClick={handleNewSession}>
          New Session
        </Button>
      </div>

      {/* Scrollbare Session-Liste */}
      <div className="flex-1 overflow-y-auto p-2">
        {sortedSessions.length === 0 && (
          <p className="p-2 text-xs text-muted-foreground">No sessions yet.</p>
        )}
        {sortedSessions.map((session) => (
          <button
            key={session.id}
            onClick={() => navigate(`/sessions/${session.id}`)}
            className={cn(
              "mb-1 w-full rounded-md px-2 py-1.5 text-left text-xs transition-colors hover:bg-muted",
              session.id === activeSessionId && "bg-primary text-primary-foreground hover:bg-primary/90"
            )}
          >
            <span className="block truncate font-medium">{session.name}</span>
            <span
              className={cn(
                "block truncate text-[10px]",
                session.id === activeSessionId
                  ? "text-primary-foreground/70"
                  : "text-muted-foreground"
              )}
            >
              {new Date(session.created_at).toLocaleDateString()}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
