#!/usr/bin/env python3
"""Push StokAPI receiver workflow — delegates to monorepo scripts/n8n_publish.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISH = REPO_ROOT / "scripts" / "n8n_publish.py"
WORKFLOW_ID = "t160mzGPYYlJcrjZ"
JSON_PATH = REPO_ROOT / "n8n/workflows/cdp_stokapi.json"
SDK_PATH = REPO_ROOT / "n8n/sdk/cdp_stokapi.workflow.ts"


def main() -> int:
    if not PUBLISH.exists():
        print(f"Missing {PUBLISH}", file=sys.stderr)
        return 1
    cmd = [
        sys.executable,
        str(PUBLISH),
        f"--workflow-id={WORKFLOW_ID}",
        f"--json={JSON_PATH}",
        f"--sdk={SDK_PATH}",
        "--description=API Diversos cdp_stokapi sync",
        "--publish",
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
