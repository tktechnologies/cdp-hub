"""Unit tests for proxy_site_smoke case selection (no browser)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import proxy_site_smoke as smoke  # noqa: E402


def test_default_rollout_excludes_archived() -> None:
    args = argparse.Namespace(
        site=None,
        sku=None,
        brand="",
        sites=None,
        from_env=False,
        include_archived=False,
        timeout_seconds=120.0,
        output="",
        json=False,
    )
    cases = smoke._cases_from_args(args)
    sites = {case[0] for case in cases}
    assert "melibox" in sites
    assert "goparts" not in sites
    assert "procurapecas" not in sites


def test_include_archived_adds_cloudflare_sites() -> None:
    args = argparse.Namespace(
        site=None,
        sku=None,
        brand="",
        sites=None,
        from_env=False,
        include_archived=True,
        timeout_seconds=120.0,
        output="",
        json=False,
    )
    sites = {case[0] for case in smoke._cases_from_args(args)}
    assert {"goparts", "procurapecas"}.issubset(sites)
