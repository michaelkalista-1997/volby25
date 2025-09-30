#!/usr/bin/env bash
set -euo pipefail

python start_collector.py &
COLLECTOR_PID=$!

trap "kill $COLLECTOR_PID" EXIT

python start_webapp.py
