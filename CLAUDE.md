**Projekt-Info:**
- Projektname: [SECCENTER]
- Stack: [TECHNOLOGIEN]
- Test-Befehl: [TEST_COMMAND]
- Lint-Befehl: [LINT_COMMAND]
- Build-Befehl: [BUILD_COMMAND]

**Coding-Regeln (IMMER einhalten):**
- Kommentare und Variablennamen auf Deutsch
- Maximale Dateigröße: 300 Zeilen — bei Überschreitung aufteilen
- Keine `any` in TypeScript
- Commits: immer mit `feat:`, `fix:`, `chore:`, `docs:` Prefix
- Kein direktes Arbeiten auf `main` oder `master` Branch
- Neue Packages nur nach ausdrücklicher Genehmigung installieren

**Was Claude NIEMALS tun darf:**
- `.env` Dateien oder andere Secrets lesen oder bearbeiten
- Direkt auf `main`/`master` pushen oder committen
- Produktions-Konfigurationen ändern
- API-Keys oder Passwörter in Code schreiben
- Dateien außerhalb des Projekts ändern

**Sub-Agent Routing Regeln:**
- 3+ unabhängige Aufgaben → Sub-Agents parallel starten
- Aufgabe braucht Hauptkontext → direkt im Hauptagent lösen
- Große Codebase durchsuchen → Explore Agent verwenden
- Wiederholende Technik erkannt → Skill erstellen
- Isolierte Expertenaufgabe → Sub-Agent + passender Skill

**Memory & Kontext:**
- Wenn Context Window voll wird: `/compact` nutzen
- Wichtige Erkenntnisse in `.claude/memory/` festhalten
- Projektspezifische Muster sofort als Skill anlegen
