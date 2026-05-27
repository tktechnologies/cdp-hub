"""Headed terminal demo: one SKU per scraper with plain-language Rich output.

Used by ``make interview-demo`` and ``POST /api/v1/demo/interview``.
"""

# ruff: noqa: E402,I001

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from src.models.schemas import SiteId, SiteResult
import src.scrapers as scrapers_registry
from src.scrapers import shutdown_all_scrapers

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from demo_scraper_runs import _get_demo_scraper, _summarize_site_result

# Active production sites + eBay (archived). No GoParts/ProcuraPeças in headed demo.
# Melibox uses Royal IP / residential proxy when PROXY_ROTATION_ENABLED=true.
DEMO_CASES: list[dict[str, Any]] = [
    {"id": "gm", "site": "gm", "sku": "93240598", "brand": "GM"},
    {"id": "ml", "site": "ml", "sku": "51766536", "brand": ""},
    {"id": "vw", "site": "vw", "sku": "5X9827550A", "brand": "VW"},
    {"id": "eu", "site": "eu", "sku": "03L115562", "brand": "VW"},
    {"id": "pecadireta", "site": "pecadireta", "sku": "7091011", "brand": ""},
    {"id": "melibox", "site": "melibox", "sku": "51766536", "brand": ""},
    {"id": "ebay", "site": "ebay", "sku": "5473368", "brand": ""},
]

_SITE_LABELS: dict[str, str] = {
    "gm": "Chevrolet (GM)",
    "ml": "Mercado Livre",
    "vw": "VW Oficial",
    "eu": "Importados Europa",
    "pecadireta": "Peça Direta",
    "melibox": "Melibox (Royal IP BR residential)",
    "ebay": "eBay (arquivado)",
}


def _format_money_display(amount: float, currency: str) -> str:
    """Human-friendly money string for terminal panels."""
    if currency.upper() in ("BRL", "R$"):
        formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    return f"{currency} {amount:,.2f}"


def _case_status(summary: dict[str, Any]) -> str:
    if summary.get("site_status") == "success" and summary.get("best_price"):
        return "success"
    return str(summary.get("site_status") or summary.get("job_status") or "unknown")


def _filter_cases(site_filter: str | None) -> list[dict[str, Any]]:
    if not site_filter:
        return list(DEMO_CASES)
    allowed = {s.strip().lower() for s in site_filter.split(",") if s.strip()}
    return [case for case in DEMO_CASES if case["site"] in allowed]


def _render_site_panel(console: Console, summary: dict[str, Any]) -> None:
    site = summary["site"]
    label = _SITE_LABELS.get(site, site.upper())
    sku = summary["sku"]
    status = _case_status(summary)
    best = summary.get("best_price") or {}

    if best.get("price") is not None:
        price_line = _format_money_display(float(best["price"]), str(best.get("currency") or "BRL"))
        match_line = "SIM" if best.get("exact_match") else "NAO"
        headline = f"[bold green]{price_line}[/bold green]\nParte encontrada: {best.get('sku_found', sku)} · match exato: {match_line}"
    else:
        err = summary.get("error_message") or status
        headline = f"[bold yellow]Sem preço claro[/bold yellow]\n{err}"

    table = Table(show_header=True, header_style="bold", title="Amostra de anúncios")
    table.add_column("Preço", style="cyan")
    table.add_column("SKU", style="white")
    table.add_column("Exato?", justify="center")
    table.add_column("Título", overflow="fold")
    for row in (summary.get("prices") or [])[:5]:
        price = row.get("price")
        price_txt = _format_money_display(float(price), str(row.get("currency") or "BRL")) if price else "—"
        table.add_row(
            price_txt,
            str(row.get("sku_found") or "—"),
            "SIM" if row.get("exact_match") else "NAO",
            str(row.get("title") or "—")[:60],
        )
    if not summary.get("prices"):
        table.add_row("—", "—", "—", "Nenhum card retornado")

    console.print(
        Panel(
            f"{headline}\n\nTempo: {summary.get('search_time_ms', 0)} ms · Resultados: {summary.get('total_results', 0)}",
            title=f"{label} · SKU {sku}",
            border_style="green" if status == "success" else "yellow",
        )
    )
    console.print(table)
    console.print()


async def _run_case(
    case: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    site_id = SiteId(case["site"])
    run_case = {**case, "site": site_id}
    scraper = None
    try:
        scraper, _is_archived = await _get_demo_scraper(site_id)
        result: SiteResult = await asyncio.wait_for(
            scraper.scrape_sku(case["sku"], case.get("brand") or ""),
            timeout=timeout_seconds,
        )
        summary = _summarize_site_result(run_case, result)
    except TimeoutError:
        summary = {
            "case_id": case["id"],
            "site": case["site"],
            "sku": case["sku"],
            "brand": case.get("brand") or "",
            "job_id": None,
            "job_status": "timeout",
            "site_status": "timeout",
            "error_message": f"Timed out after {timeout_seconds} seconds.",
            "search_time_ms": 0,
            "total_results": 0,
            "best_price": None,
            "prices": [],
            "raw_site_result": None,
        }
    except Exception as exc:
        summary = {
            "case_id": case["id"],
            "site": case["site"],
            "sku": case["sku"],
            "brand": case.get("brand") or "",
            "job_id": None,
            "job_status": "error",
            "site_status": "error",
            "error_message": str(exc),
            "search_time_ms": 0,
            "total_results": 0,
            "best_price": None,
            "prices": [],
            "raw_site_result": None,
        }
    else:
        pass
    finally:
        if scraper is not None:
            await scraper.shutdown()
            scrapers_registry._active_scrapers.pop(site_id, None)

    summary["status"] = _case_status(summary)
    return summary


async def _run(
    output_path: Path,
    timeout_seconds: float,
    site_filter: str | None,
    headless: bool,
    proxy_rotation_enabled: bool,
) -> int:
    from src.config import settings

    settings.playwright_headless = headless
    settings.proxy_rotation_enabled = proxy_rotation_enabled
    if proxy_rotation_enabled and not settings.proxy_urls:
        Console().print(
            "[yellow]Aviso: PROXY_ROTATION_ENABLED=true mas PROXY_URLS vazio — "
            "configure Royal IP BR residential no .env para o Melibox.[/yellow]"
        )

    cases = _filter_cases(site_filter)
    console = Console()
    summaries: list[dict[str, Any]] = []

    proxy_note = (
        "sim (Royal IP / residential para Melibox)"
        if proxy_rotation_enabled
        else "nao"
    )
    console.print(
        Panel(
            f"[bold]Demo interview CDP[/bold]\n"
            f"Sites: {len(cases)} · Headless: {'sim' if headless else 'nao (janela visivel)'}\n"
            f"Proxy rotation: {proxy_note}\n"
            f"Timeout por site: {timeout_seconds:.0f}s",
            border_style="blue",
        )
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Rodando scrapers…", total=len(cases))
            for case in cases:
                label = _SITE_LABELS.get(case["site"], case["site"])
                progress.update(task_id, description=f"{label} ({case['sku']})")
                summary = await _run_case(case, timeout_seconds)
                summaries.append(summary)
                _render_site_panel(console, summary)
                progress.advance(task_id)
    finally:
        output = {
            "generated_at": datetime.now(UTC).isoformat(),
            "purpose": "interview terminal demo",
            "headless": headless,
            "cases": summaries,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

        success = sum(1 for row in summaries if row.get("status") == "success")
        recap = Table(title="Recap (para apresentação)")
        recap.add_column("Site")
        recap.add_column("SKU")
        recap.add_column("Status")
        recap.add_column("Melhor preço")
        for row in summaries:
            best = row.get("best_price") or {}
            if best.get("price") is not None:
                price_txt = _format_money_display(float(best["price"]), str(best.get("currency") or "BRL"))
            else:
                price_txt = "—"
            recap.add_row(
                _SITE_LABELS.get(row["site"], row["site"]),
                row["sku"],
                row.get("status", "?"),
                price_txt,
            )
        console.print(recap)
        console.print(
            f"\n[bold]Concluido:[/bold] {success}/{len(summaries)} sites com preço claro.\n"
            f"JSON: {output_path}\n"
        )

        try:
            await asyncio.wait_for(shutdown_all_scrapers(), timeout=30)
        except TimeoutError:
            console.print("[yellow]Aviso: timeout ao fechar browsers[/yellow]")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        default="docs/validation/latest_interview_demo_results.json",
        help="Where to write JSON results.",
    )
    parser.add_argument(
        "--sites",
        default="",
        help="Comma-separated site ids (default: all registered + archived).",
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without visible browser (default: headed for presentations).",
    )
    parser.add_argument(
        "--proxy-rotation",
        action="store_true",
        help="Enable PROXY_ROTATION_ENABLED (Royal IP BR residential for Melibox demo).",
    )
    args = parser.parse_args()
    site_filter = args.sites.strip() or None
    proxy_enabled = args.proxy_rotation or (
        os.environ.get("PROXY_ROTATION_ENABLED", "").lower() in {"1", "true", "yes"}
    )
    return asyncio.run(
        _run(
            Path(args.json_out),
            args.timeout_seconds,
            site_filter,
            args.headless,
            proxy_enabled,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
