#!/bin/bash
# Launch WallPicker with the best available Python interpreter.
#
# Interpreter availability is probed BEFORE running the app (M22): a non-zero
# exit from the application itself must never trigger a relaunch — the exit
# code propagates. Only an unavailable interpreter falls through to the next
# candidate.
cd "$(dirname "$0")"

# probe <interpreter-cmd...> -> succeeds only if the interpreter can run.
probe() {
    "$@" -c '' >/dev/null 2>&1
}

# 1) mise-managed Python
if command -v mise >/dev/null 2>&1 && mise where python >/dev/null 2>&1 \
   && probe mise exec -- python; then
    env MISE_AUTO_INSTALL=0 mise exec -- python launcher.py
    exit $?
fi

# 2) project virtualenv
if [ -x ".venv/bin/python" ] && probe .venv/bin/python; then
    .venv/bin/python launcher.py
    exit $?
fi

# 3) system Python (last resort)
exec python3 launcher.py
