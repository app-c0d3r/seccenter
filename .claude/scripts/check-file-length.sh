#!/bin/bash

INPUT=${CLAUDE_TOOL_INPUT:-$(cat 2>/dev/null)}
# Very dirty path extraction but robust enough for a mock
FILES=$(echo "$INPUT" | grep -E -o '("[^"]+\.[a-zA-Z0-9]+")' | tr -d '"')

for FILE in $FILES; do
    if [ -f "$FILE" ]; then
        if [[ ! "$FILE" =~ \.(md|lock|json)$ ]]; then
            LINES=$(wc -l < "$FILE")
            if [ "$LINES" -gt 500 ]; then
                echo "Fehler: Die Datei $FILE überschreitet 500 Zeilen ($LINES Zeilen). Bitte aufteilen." >&2
                exit 2
            elif [ "$LINES" -gt 300 ]; then
                echo "Warnung: Die Datei $FILE hat über 300 Zeilen ($LINES Zeilen)." >&2
            fi
        fi
    fi
done

exit 0
