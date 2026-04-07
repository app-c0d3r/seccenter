#!/bin/bash

INPUT=${CLAUDE_TOOL_INPUT:-$(cat 2>/dev/null)}
FILES=$(echo "$INPUT" | grep -E -o '("[^"]+\.[a-zA-Z0-9]+")' | tr -d '"')

for FILE in $FILES; do
    if [ -f "$FILE" ]; then
        if [[ "$FILE" =~ \.(js|ts|jsx|tsx|css|json|html)$ ]]; then
            if command -v npx &> /dev/null; then
                npx prettier --write "$FILE" >/dev/null 2>&1 || true
            fi
        elif [[ "$FILE" =~ \.py$ ]]; then
            if command -v black &> /dev/null; then
                black "$FILE" >/dev/null 2>&1 || true
            fi
        fi
    fi
done

exit 0
