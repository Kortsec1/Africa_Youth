#!/usr/bin/env bash
set -euo pipefail

./scripts/generate-cert.sh
mkdir -p logs
python -m server.https_server --host 127.0.0.1 --port 8443 &
SERVER_PID=$!
python -m proxy.main --listen-host 127.0.0.1 --listen-port 9443 --policy configs/policy.yaml &
PROXY_PID=$!
echo "${SERVER_PID}" > /tmp/tls-test-server.pid
echo "${PROXY_PID}" > /tmp/tls-policy-proxy.pid
echo "server pid=${SERVER_PID}, proxy pid=${PROXY_PID}"
echo "run ./scripts/stop-local.sh to stop"
wait
