#!/usr/bin/env python3
"""Ensure n8n/workflows/cdp_notifier.json exists before DEV/prod n8n prep."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTIFIER_JSON = REPO_ROOT / "n8n" / "workflows" / "cdp_notifier.json"


def main() -> int:
    if NOTIFIER_JSON.is_file():
        print(f"OK: {NOTIFIER_JSON.relative_to(REPO_ROOT)} present")
        return 0

    print(
        f"Missing {NOTIFIER_JSON.relative_to(REPO_ROOT)}.\n"
        "Fetch the live cdp_notifier workflow from n8n "
        "(workflow ID ennI9nKin9ruPaLO on automacao.tktechnologies.com.br) "
        "and save it to that path before running make n8n-dev-workflows.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
