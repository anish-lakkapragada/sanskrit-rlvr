#!/bin/sh
set -eu
prototype_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_dir="$(CDPATH= cd -- "$prototype_dir/../../../.." && pwd)"
exec env PYTHONDONTWRITEBYTECODE=1 TMPDIR="$prototype_dir/tmp" PYTHONPATH="$prototype_dir/safety:$prototype_dir/worktree" "$repo_dir/.venv/bin/python" "$prototype_dir/run_tests.py"
