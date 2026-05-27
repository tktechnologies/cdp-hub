#!/usr/bin/env bash
# Replay n8n callbacks for bulk jobs still processing after execution 367.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a && source .env && set +a

PENDING=(
  80e8dd8e-f34d-44d6-9d66-57061d9c1745
  596a1f7b-733c-479a-9dfc-8a045a17f49e
  f9eda073-4030-4777-95bd-5dc919ea7032
  9c1f5934-8602-469b-8ab3-0fd5d847d6af
  9651e992-6283-4cd0-93e0-30b272d818a0
  8f797b90-172b-42af-9ba1-075ee78a61a5
  3c3f06ce-ff4b-47a8-b9a1-9b64d64ee5fb
)

KEY="${CDP_MUVSTOK_API_KEY:-${API_KEYS%%,*}}"
BASE="${CDP_MUVSTOK_API_BASE}"
READY=()

for jid in "${PENDING[@]}"; do
  st=$(curl -sS "$BASE/api/v1/muvstok/jobs/$jid" -H "X-API-Key: $KEY" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  if [[ "$st" == "succeeded" || "$st" == "partially_succeeded" || "$st" == "failed" ]]; then
    READY+=("$jid")
  else
    echo "skip $jid status=$st"
  fi
done

if ((${#READY[@]} == 0)); then
  echo "No terminal jobs yet."
  exit 0
fi

IDS=$(IFS=,; echo "${READY[*]}")
uv run python scripts/replay_n8n_callbacks.py --job-ids "$IDS" --delay 6
