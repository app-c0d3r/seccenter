cyber-security-cockpit/
├── .claudecode/             # Spezifische Anweisungen für Claude Code (Token-optimiert)
├── .github/                 # Workflows für CI/CD (Linting, Docker Build)
├── docs/                    # Architektur-Entscheidungen (ADR), API-Specs
├── infrastructure/          # docker-compose.yml, n8n-Workflows (.json), DB-Init-Skripte
├── packages/                # Shared Code (z.B. TypeScript Interfaces für Output-Schemata)
├── apps/
│   ├── web-ui/              # React, Zustand, UI-Komponenten (Dein Fokus)
│   ├── middleware-api/      # Python oder Node.js: DLP-Logik, n8n-Callbacks, WebSocket
│   └── agent-service/       # LangGraph, RAG-Logik, LLM-Anbindung
└── [README.md](http://readme.md/)                # Zentraler Einstiegspunkt