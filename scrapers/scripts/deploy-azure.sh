#!/usr/bin/env bash
# Deprecated path — use scripts/deploy-scraper-azure.sh from repo root.
exec "$(cd "$(dirname "$0")/../.." && pwd)/scripts/deploy-scraper-azure.sh" "$@"
