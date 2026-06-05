#!/usr/bin/env bash
set -euo pipefail

mkdir -p server/certs
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout server/certs/server.key \
  -out server/certs/server.crt \
  -days 365 \
  -subj "/CN=allowed.test" \
  -addext "subjectAltName=DNS:allowed.test,DNS:blocked.test,DNS:unknown.test,DNS:localhost,IP:127.0.0.1"
echo "created server/certs/server.crt and server/certs/server.key"
