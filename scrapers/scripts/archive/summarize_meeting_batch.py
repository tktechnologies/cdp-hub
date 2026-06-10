"""Build a meeting-friendly markdown summary from meeting_sku_batch_results.json."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

STATUS_EMOJI = {
    "success": "✅",
    "not_found": "❌",
    "no_price": "💰?",
    "blocked": "🚫",
    "error": "⚠️",
    "timeout": "⏱️",
}


def _cell(row: dict) -> str:
    st = row.get("status", "?")
    icon = STATUS_EMOJI.get(st, "•")
    if st == "success" and row.get("has_price"):
        cur = row.get("currency") or ""
        avail = row.get("availability") or "?"
        return f"{icon} **{row['price']:.2f} {cur}** ({avail})"
    if st == "no_price":
        return f"{icon} found, sem preço"
    if st == "not_found":
        return f"{icon} não encontrado"
    if st == "blocked":
        msg = (row.get("error_message") or "")[:40]
        return f"{icon} bloqueado {msg}"
    if st == "error":
        msg = (row.get("error_message") or "")[:40]
        return f"{icon} erro {msg}"
    if st == "timeout":
        return f"{icon} timeout"
    return f"{icon} {st}"


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/validation/meeting_sku_batch_results.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["results"]
    sites = sorted({r["site"] for r in rows}, key=lambda s: s)
    skus = data.get("skus") or sorted({r["sku"] for r in rows})

    by_key = {(r["sku"], r["site"]): r for r in rows}

    lines = [
        "# Meeting SKU scrape — localhost",
        "",
        f"**Generated:** {data.get('generated_at', '?')}",
        f"**Cases:** {data.get('total_cases', len(rows))}",
        "",
    ]

    # Per-site success rates
    lines.append("## Resumo por site")
    lines.append("")
    lines.append("| Site | Sucesso c/ preço | Sem preço | Não encontrado | Bloqueado | Erro/Timeout |")
    lines.append("|------|------------------|-----------|----------------|-----------|--------------|")
    for site in sites:
        site_rows = [r for r in rows if r["site"] == site]
        counts: dict[str, int] = defaultdict(int)
        for r in site_rows:
            counts[r["status"]] += 1
        priced = sum(1 for r in site_rows if r.get("has_price"))
        lines.append(
            f"| {site} | {priced} | {counts['no_price']} | {counts['not_found']} | "
            f"{counts['blocked']} | {counts['error'] + counts['timeout']} |"
        )

    lines.extend(["", "## Matriz SKU × site", ""])
    header = "| SKU | " + " | ".join(sites) + " |"
    sep = "|-----|" + "|".join(["------"] * len(sites)) + "|"
    lines.extend([header, sep])
    for sku in skus:
        cells = [_cell(by_key.get((sku, site), {"status": "missing"})) for site in sites]
        lines.append(f"| `{sku}` | " + " | ".join(cells) + " |")

    # Per-SKU rollup
    lines.extend(["", "## Resumo por SKU", ""])
    for sku in skus:
        sku_rows = [r for r in rows if r["sku"] == sku]
        priced_sites = [r["site"] for r in sku_rows if r.get("has_price")]
        blocked = [r["site"] for r in sku_rows if r["status"] == "blocked"]
        not_found = [r["site"] for r in sku_rows if r["status"] == "not_found"]
        lines.append(f"### `{sku}`")
        lines.append(f"- **Com preço:** {', '.join(priced_sites) or '—'}")
        lines.append(f"- **Bloqueado:** {', '.join(blocked) or '—'}")
        lines.append(f"- **Não encontrado:** {', '.join(not_found) or '—'}")
        lines.append("")

    out = path.with_suffix(".md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
