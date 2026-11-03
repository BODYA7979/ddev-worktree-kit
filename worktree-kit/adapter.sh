#!/usr/bin/env bash
#ddev-generated
# Run from the new worktree, even on a branch predating add-on installation.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
if [[ -f "$root/.ddev/worktree-kit/manager.py" ]]; then
  manager="$root/.ddev/worktree-kit/manager.py"
else
  common=$(git rev-parse --path-format=absolute --git-common-dir)
  manager="$(dirname "$common")/.ddev/worktree-kit/manager.py"
fi
exec python3 "$manager" "$@"
