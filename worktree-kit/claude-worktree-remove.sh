#!/usr/bin/env bash
#ddev-generated
set -euo pipefail
directory=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
project=$(cd "$directory/../.." && pwd -P)
exec python3 "$directory/manager.py" --repository "$project" --path "$project" claude-remove
