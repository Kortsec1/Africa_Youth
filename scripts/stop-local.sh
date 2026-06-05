#!/usr/bin/env bash
set -euo pipefail

for file in /tmp/tls-policy-proxy.pid /tmp/tls-test-server.pid; do
  if [[ -f "${file}" ]]; then
    pid="$(cat "${file}")"
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}"
      echo "stopped ${pid}"
    fi
    rm -f "${file}"
  fi
done
