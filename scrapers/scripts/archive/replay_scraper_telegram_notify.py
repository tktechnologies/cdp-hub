#!/usr/bin/env python3
"""Replay scraper webhook to deliver Telegram completion (e.g. after formatter fix)."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / "muvstok-api" / ".env"


def _secret() -> str:
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith("CALLBACK_WEBHOOK_SECRET="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("CALLBACK_WEBHOOK_SECRET not found")


def main() -> int:
    body = {
        "job_id": "0d4129be-ef00-4264-adbf-5c2e70c28b3c",
        "status": "completed",
        "total_items": 1,
        "duration_seconds": 13.24,
        "results": [
            {
                "sku": "8200505566",
                "total_results": 1,
                "best_price": {
                    "sku_searched": "8200505566",
                    "sku_found": "8200505566",
                    "exact_match": True,
                    "site": "eu",
                    "site_name": "EU Imports",
                    "price": 39.76,
                    "currency": "USD",
                    "product_url": "https://export.fastparts.is/",
                },
                "site_results": [
                    {"site": "gm", "site_name": "GM", "status": "not_found", "results": []},
                    {"site": "ml", "site_name": "ML", "status": "not_found", "results": []},
                    {"site": "eu", "site_name": "EU Imports", "status": "success", "results": []},
                ],
            }
        ],
    }
    query = (
        "notify=telegram&batch_group_id=bg-mpn02vib-x0zh4z&dual_run=scraper"
        "&command_route=sku_text&chat_id=7894125008&ad_hoc=true"
    )
    url = f"https://automacao.tktechnologies.com.br/webhook/scraper-result?{query}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "x-webhook-secret": _secret()},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.status, resp.read().decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
