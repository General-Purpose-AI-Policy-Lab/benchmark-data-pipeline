#!/bin/sh
# Start the dashboard server and open it in a browser. Ctrl-C stops it.
cd "$(dirname "$0")/.." || exit 1
(sleep 1; (open http://localhost:8130 || xdg-open http://localhost:8130) 2>/dev/null) &
exec python3 scripts/serve.py
