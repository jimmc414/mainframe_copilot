#!/bin/bash
# Start TN3270 Bridge API Server

cd "$(dirname "$0")"
source venv/bin/activate

echo "Starting TN3270 Bridge API on http://127.0.0.1:8080"
echo "Press Ctrl+C to stop"

python -m tn3270_bridge.api "$@"