#!/bin/sh
set -eu
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  exec python3 launch.py
elif command -v python >/dev/null 2>&1; then
  exec python launch.py
else
  echo "Python 3.11 or 3.12 is required. Install Python and try again." >&2
  exit 1
fi
