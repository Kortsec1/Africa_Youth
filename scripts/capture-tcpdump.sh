#!/usr/bin/env bash
set -euo pipefail

mkdir -p captures
iface="${1:-lo0}"
sudo tcpdump -i "${iface}" port 9443 -w captures/tls-local-test.pcap
