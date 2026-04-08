/**
 * React-Router Konfiguration fuer SECCENTER
 * Definiert alle Anwendungsrouten
 */
import { createBrowserRouter } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { SessionPage } from "./pages/SessionPage";

/** Zentraler Browser-Router mit allen Anwendungsrouten */
export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  { path: "/sessions/:sessionId", element: <SessionPage /> },
]);
