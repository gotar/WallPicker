#!/bin/bash
# Launch WallPicker with the best available Python interpreter.
#
# Interpreter selection happens BEFORE running the app: a non-zero exit from
# the application itself must never trigger a relaunch (M22) — only the
# unavailability of an interpreter falls through to the next candidate.
cd "$(dirname "$0")"

run_python() {
    # $@ = command prefix that provides a python interpreter
    "$@" -c '' >/dev/null 2>&1 || return 1
    env MISE_AUTO_INSTALL=0 "$@" launcher.py
}

if command -v mise >/dev/null 2>&1 && mise where python >/dev/null 2>&1; then
    if run_python mise exec -- python; then
        exit 0
    fi
fi

if [ -x ".venv/bin/python" ]; then
    if run_python .venv/bin/python; then
        exit 0
    fi
fi

exec python3 launcher.py
