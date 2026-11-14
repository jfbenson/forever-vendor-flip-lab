#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  exec python3 launch.py "$@"
else
  echo "Python 3.10+ is required. Install it and retry." >&2
  exit 1
fi
