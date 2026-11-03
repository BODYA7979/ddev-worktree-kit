#!/usr/bin/env bash
#ddev-generated
set -euo pipefail
directory=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
project=$(cd "$directory/../.." && pwd -P)
target=${CODEX_WORKTREE_PATH:?Codex must provide CODEX_WORKTREE_PATH}
case "$target" in /*) ;; *) echo 'CODEX_WORKTREE_PATH must be absolute' >&2; exit 1 ;; esac
exec python3 "$directory/manager.py" --repository "$project" --path "$target" teardown --automatic --apply --yes
