#!/bin/bash

if ! command -v git &> /dev/null; then
    exit 0
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    exit 0
fi

BRANCH=$(git branch --show-current)

if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo "Fehler: Direktes Arbeiten auf $BRANCH ist nicht erlaubt. Bitte erstelle einen Feature-Branch!" >&2
    exit 2
fi

exit 0
