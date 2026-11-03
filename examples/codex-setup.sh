#!/usr/bin/env bash
set -euo pipefail
python3 -c 'import os, subprocess; data = subprocess.check_output(["git", "worktree", "list", "--porcelain", "-z"]); main = os.fsdecode(data.split(bytes([0]), 1)[0][9:]); os.execvp("bash", ["bash", main + "/.ddev/worktree-kit/codex-setup.sh"])'
