---
name: security-check
description: >
  Aktiviere wenn: Authentifizierung, Autorisierung, API-Keys, Passwörter,
  Benutzereingaben, Datenbankabfragen, oder externe Daten verarbeitet werden.
---

**Sicherheits-Checkliste:**
- Keine Secrets im Code
- Benutzereingaben immer validieren und sanitizen
- Parameterisierte Queries (kein String-Concatenation für SQL)
- HTTPS für alle externen Verbindungen
- Minimale Berechtigungen (Principle of Least Privilege)
- Fehler-Messages nie sensible Infos ausgeben lassen
