#!/usr/bin/env bash
set -euo pipefail

python start_collector.py &
COLLECTOR_PID=$!

python start_webapp.py &
WEBAPP_PID=$!

terminate() {
  trap - SIGINT SIGTERM EXIT
  for pid in "$COLLECTOR_PID" "$WEBAPP_PID"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait "$COLLECTOR_PID" "$WEBAPP_PID" 2>/dev/null || true
}

trap terminate SIGINT SIGTERM EXIT

wait -n "$COLLECTOR_PID" "$WEBAPP_PID"
terminate
