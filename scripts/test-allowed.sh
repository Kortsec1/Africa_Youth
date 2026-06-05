#!/usr/bin/env bash
set -euo pipefail

curl --noproxy "*" -vk --resolve allowed.test:9443:127.0.0.1 https://allowed.test:9443/
