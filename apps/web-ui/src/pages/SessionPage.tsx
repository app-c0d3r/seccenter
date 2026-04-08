/**
 * Session-Seite: Laedt die aktive Session und rendert die App-Shell
 */
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useSessionStore } from "@/store/sessionStore";
import { AppShell } from "@/layout/AppShell";

/** Session-Seite – setzt die aktive Session und zeigt die Haupt-UI an */
export function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const setActiveSession = useSessionStore((state) => state.setActiveSession);

  useEffect(() => {
    if (sessionId) {
      setActiveSession(sessionId);
    }
  }, [sessionId, setActiveSession]);

  return <AppShell />;
}
