#!/bin/bash
cd "$(dirname "$0")"

if command -v mise >/dev/null 2>&1 && mise where python >/dev/null 2>&1; then
    if env MISE_AUTO_INSTALL=0 mise exec -- python launcher.py; then
        exit 0
    fi
fi

if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python launcher.py
fi

exec python3 launcher.py
