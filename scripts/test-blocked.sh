#!/usr/bin/env bash
set -euo pipefail

curl --noproxy "*" -vk --resolve blocked.test:9443:127.0.0.1 https://blocked.test:9443/
