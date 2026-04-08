```json
{
  "type": "object",
  "properties": {
    "header": {
      "type": "object",
      "properties": {
        "when": { "type": "string", "description": "ISO Timestamp des Vorfalls" },
        "what": { "type": "string", "description": "Kurze, prägnante Zusammenfassung (max 100 Zeichen)" },
        "who": { "type": "string", "description": "Name des Analysten oder 'System'" }
      },
      "required": ["when", "what", "who"]
    },
    "body": {
      "type": "object",
      "properties": {
        "assets_summary": {
          "type": "array",
          "description": "Liste der analysierten Assets und deren Enrichment-Ergebnisse",
          "items": {
            "type": "object",
            "properties": {
              "asset_value": { "type": "string" },
              "findings": { "type": "string", "description": "Zusammenfassung der n8n-Daten" }
            }
          }
        }
      },
      "required": ["assets_summary"]
    },
    "foot": {
      "type": "object",
      "properties": {
        "conclusion": { "type": "string", "description": "Fazit der Analyse" },
        "next_steps": { "type": "array", "items": { "type": "string" } },
        "tips_and_measures": { "type": "array", "items": { "type": "string" } }
      },
      "required": ["conclusion", "next_steps", "tips_and_measures"]
    }
  },
  "required": ["header", "body", "foot"]
}
```