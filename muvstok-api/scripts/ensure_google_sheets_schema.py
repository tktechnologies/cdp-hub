#!/usr/bin/env python3
"""Ensure cdp_resultados Detalhado headers and Painel formulas.

Delegates to apply_google_sheets_audit.py (v2 schema).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_google_sheets_audit import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
