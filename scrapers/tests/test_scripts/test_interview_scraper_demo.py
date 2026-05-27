"""Interview demo script contract tests (no live browser)."""

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module(relative: str):
    path = PROJECT_ROOT / "scripts" / relative
    spec = importlib.util.spec_from_file_location(relative.replace("/", "_"), path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_interview_demo_cases_match_registry() -> None:
    from src.scrapers import SCRAPER_REGISTRY

    mod = _load_script_module("interview_scraper_demo.py")
    demo_sites = {c["site"] for c in mod.DEMO_CASES}
    expected = {s.value for s in SCRAPER_REGISTRY} | {"ebay"}
    assert demo_sites == expected
    assert "goparts" not in demo_sites
    assert "procurapecas" not in demo_sites
    assert "melibox" in demo_sites


def test_interview_demo_uses_validated_sku_map() -> None:
    mod = _load_script_module("interview_scraper_demo.py")

    assert {case["site"]: case["sku"] for case in mod.DEMO_CASES} == {
        "gm": "93240598",
        "ml": "51766536",
        "vw": "5X9827550A",
        "eu": "03L115562",
        "pecadireta": "7091011",
        "melibox": "51766536",
        "ebay": "5473368",
    }


def test_format_money_display_brl() -> None:
    mod = _load_script_module("interview_scraper_demo.py")
    out = mod._format_money_display(1234.56, "BRL")
    assert out.startswith("R$")
    assert "1.234" in out or "1234" in out


@pytest.mark.asyncio
async def test_inspect_scrape_db_script_runs() -> None:
    from src.models.database import init_db

    await init_db()
    mod = _load_script_module("inspect_scrape_db.py")
    rc = await mod._run()
    assert rc == 0
