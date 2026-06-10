#!/usr/bin/env python3
"""Smoke-test sheet helper logic via Node (same JS as n8n)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPERS = REPO_ROOT / "n8n/lib/muvstok_sheet_helpers.js"

NODE_TEST = """
const helpers = require('fs').readFileSync(process.argv[1], 'utf8');
eval(helpers);
const rows = JSON.parse(process.argv[2]);
const results = rows.map((row) => {
  const sku = row.sku;
  return {
    sku,
    tipo_code: stockTypeCode(row),
    sale: naSalePriceFromRow(row),
    cost: naCostPriceFromRow(row),
    title: productTitle(row),
    product_url: productUrlForSheet(sku, row),
    status: normalizeResultStatus(row.sku_result, [row]),
    has_valid_price: hasValidPrice([row]),
    empresa: companyLabel(row),
    uf: sellerUf(row),
    cnpj: cnpjFromRow(row),
  };
});
const offer = bestOfferFromListings(rows);
console.log(JSON.stringify({
  results,
  offer,
  link: productUrlForSheet('x', rows[0]),
  blocked_status: normalizeResultStatus('http_403', []),
  blocked_health: normalizeSourceHealth('BLOCKED', { sku_result: 'BLOCKED' }),
}, null, 2));
"""


def run(rows: list[dict]) -> dict:
    proc = subprocess.run(
        ["node", "-e", NODE_TEST, str(HELPERS), json.dumps(rows)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def main() -> None:
    rows = [
        {
            "sku": "22781768",
            "nomeFilial": "Filial Centro",
            "qtdeEstoque": 3,
            "tipoEstoque": "Vivo",
            "valorPrecoVenda": 150.5,
            "valorCustoMedio": 120,
            "fabricante": "GM",
            "produto": "Parachoque",
            "telefone": "11 99999-0000",
            "razaoSocial": "Centro Auto Pecas Ltda",
            "estado": "Parana",
            "cnpj": "05.788.992/0001-87",
        },
        {
            "sku": "22781768",
            "nomeFilial": "Filial Norte",
            "qtdeEstoque": 1,
            "tipoEstoque": 3,
            "valorPrecoVenda": 200,
            "valorCustoMedio": 80,
            "produto": "Farol",
            "uf": "SP",
            "cnpjFilial": "20379987000708",
        },
        {
            "sku": "22781768",
            "nomeFilial": "Sem Venda",
            "qtdeEstoque": 1,
            "tipoEstoque": "Morto",
            "valorCustoMedio": 50,
            "produto": "Retrovisor",
        },
    ]
    out = run(rows)

    assert out["results"][0]["tipo_code"] == "1", out["results"][0]
    assert out["results"][0]["sale"] == "150,50", out["results"][0]
    assert out["results"][0]["cost"] == "120,00", out["results"][0]
    assert out["results"][1]["tipo_code"] == "3", out["results"][1]
    assert out["results"][1]["sale"] == "200,00", out["results"][1]
    assert out["results"][1]["cost"] == "80,00", out["results"][1]
    assert out["results"][2]["tipo_code"] == "3", out["results"][2]
    assert out["results"][2]["sale"] == "", out["results"][2]
    assert out["results"][2]["cost"] == "50,00", out["results"][2]
    assert "[1]" in out["results"][0]["title"] or "[1]" in out["results"][0]["title"].lower()

    assert out["results"][0]["product_url"] == "", out["results"][0]
    assert out["results"][0]["status"] == "FOUND_PRICE", out["results"][0]
    assert out["results"][0]["has_valid_price"] is True, out["results"][0]
    assert out["results"][0]["empresa"] == "Centro Auto Pecas Ltda", out["results"][0]
    assert out["results"][0]["uf"] == "PR", out["results"][0]
    assert out["results"][0]["cnpj"] == "05788992000187", out["results"][0]
    assert out["results"][1]["uf"] == "SP", out["results"][1]
    assert out["results"][1]["cnpj"] == "20379987000708", out["results"][1]
    assert out["results"][2]["status"] == "NO_PRICE", out["results"][2]
    assert out["results"][2]["has_valid_price"] is False, out["results"][2]
    assert out["link"] == "", out
    assert out["offer"]["bestPrice"] == 150.5, out["offer"]
    assert out["blocked_status"] == "BLOCKED", out
    assert out["blocked_health"] == "BLOCKED", out
    assert "bestContact" not in out["offer"]
    print("OK", json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
