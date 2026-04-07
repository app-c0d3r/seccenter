#!/bin/bash

INPUT=${CLAUDE_TOOL_INPUT:-$(cat 2>/dev/null)}

if echo "$INPUT" | grep -iE '\.env(\..+)?|id_rsa|\.pem$|\.key$|credential|secret|\.pfx$|\.p12$'; then
    echo "Fehler: Zugriff auf sensible Dateien (Secrets) strengstens untersagt!" >&2
    exit 2
fi

exit 0
