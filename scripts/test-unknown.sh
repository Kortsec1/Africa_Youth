#!/usr/bin/env bash
set -euo pipefail

curl --noproxy "*" -vk --resolve unknown.test:9443:127.0.0.1 https://unknown.test:9443/
