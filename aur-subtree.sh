#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./aur-subtree.sh <command>

Commands:
  remote  Ensure the AUR git remote exists
  pull    Pull AUR history into aur/
  push    Push aur/ subtree to AUR
  sync    Pull then push
EOF
}

ensure_remote() {
  if ! git remote get-url aur >/dev/null 2>&1; then
    git remote add aur aur@aur.archlinux.org:wallpicker.git
  fi
}

command=${1:-}
if [[ -z "$command" ]]; then
  usage
  exit 1
fi

case "$command" in
  remote)
    ensure_remote
    ;;
  pull)
    ensure_remote
    git subtree pull --prefix aur aur master
    ;;
  push)
    ensure_remote
    git subtree push --prefix aur aur master
    ;;
  sync)
    ensure_remote
    git subtree pull --prefix aur aur master
    git subtree push --prefix aur aur master
    ;;
  *)
    usage
    exit 1
    ;;
esac
