"""Tests for local scraper validation manifest gates."""

import json

import pytest

from scripts.validate_local_scrapers import _load_manifest


def _case(site: str, case_id: str) -> dict:
    return {
        "id": case_id,
        "site": site,
        "sku": f"{site}-SKU-123",
        "brand": "",
        "expect_result": True,
        "expected_currency": "BRL",
        "expected_condition": "new",
        "expected_price_min": 1.0,
        "expected_price_max": 999.0,
        "evidence_url": f"https://example.com/{site}",
    }


def _manifest() -> dict:
    return {
        "version": 1,
        "require_real_scrapers": True,
        "cases": [
            _case("gm", "gm-known"),
            _case("ml", "ml-known"),
            _case("vw", "vw-known"),
            _case("eu", "eu-known"),
            _case("pecadireta", "pecadireta-known"),
            _case("melibox", "melibox-known"),
        ],
    }


def test_manifest_requires_all_real_scraper_sites(tmp_path):
    manifest = _manifest()
    manifest["cases"] = manifest["cases"][:-1]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing required"):
        _load_manifest(path)


def test_manifest_rejects_placeholders(tmp_path):
    manifest = _manifest()
    manifest["cases"][0]["sku"] = "REPLACE_WITH_REAL_SKU"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RuntimeError, match="placeholders"):
        _load_manifest(path)


def test_manifest_loads_valid_cases(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(_manifest()), encoding="utf-8")

    cases = _load_manifest(path)

    assert len(cases) == 6
    assert {case.site for case in cases} == {
        "gm",
        "ml",
        "vw",
        "eu",
        "pecadireta",
        "melibox",
    }
