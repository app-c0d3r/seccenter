/**
 * Startseite: Erstellt automatisch eine neue Session und leitet weiter
 */
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/api/apiClient";
import { useSessionStore } from "@/store/sessionStore";

/** Startseite – legt beim Laden sofort eine neue Session an */
export function HomePage() {
  const navigate = useNavigate();
  const addSession = useSessionStore((state) => state.addSession);

  useEffect(() => {
    // Neue Session anlegen und direkt zur Session-Seite navigieren
    apiClient
      .createSession("New Analysis")
      .then((session) => {
        addSession(session);
        navigate(`/sessions/${session.id}`, { replace: true });
      })
      .catch((error: unknown) => {
        console.error("Session konnte nicht erstellt werden:", error);
      });
  }, [addSession, navigate]);

  return (
    <div className="flex h-screen items-center justify-center">
      <p className="text-muted-foreground">Creating session...</p>
    </div>
  );
}
