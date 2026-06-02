#!/usr/bin/env python3
"""Backward-compatible wrapper — use monorepo scripts/n8n_publish.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISH = REPO_ROOT / "scripts" / "n8n_publish.py"


def main() -> int:
    if not PUBLISH.exists():
        print(f"Missing {PUBLISH}", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(PUBLISH), *sys.argv[1:]]
    # Legacy callers pass --sdk without --json; map workflow-id to default JSON
    if "--json" not in sys.argv:
        wf_id = None
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg.startswith("--workflow-id="):
                wf_id = arg.split("=", 1)[1]
            elif arg == "--workflow-id" and i < len(sys.argv):
                wf_id = sys.argv[i + 1]
        mapping = {
            "6id6dkinK9xTLfsb": REPO_ROOT / "n8n/workflows/cdp_router.json",
            "VfBSV3WU6on8BXm8": REPO_ROOT / "n8n/workflows/cdp_scraper.json",
            "t160mzGPYYlJcrjZ": REPO_ROOT / "n8n/workflows/cdp_stokapi.json",
        }
        if wf_id and wf_id in mapping:
            cmd.extend(["--json", str(mapping[wf_id])])
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
