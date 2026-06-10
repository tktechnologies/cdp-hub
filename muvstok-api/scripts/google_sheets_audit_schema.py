"""Canonical Google Sheets audit schema for cdp_resultados."""

from __future__ import annotations

SPREADSHEET_ID = "1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo"
DETALHADO_GID = 1185876304

# v2 Detalhado — aligned with receiver output after 2026-06 audit.
CANONICAL_DETALHADO_HEADERS: list[str] = [
    "job_id",
    "sku_pesquisado",
    "sku_encontrado",
    "correspondencia_exata",
    "site",
    "codigo_site",
    "status_resultado",
    "has_valid_price",
    "source_health",
    "preco",
    "preco-medio",
    "moeda",
    "condicao",
    "vendedor",
    "uf",
    "empresa",
    "cnpj",
    "url_produto",
    "titulo_bruto",
    "marca",
    "regiao",
    "coletado_em",
    "tempo_busca_ms",
    "fonte_pipeline",
]

DETALHADO_COLUMNS_REMOVE = [
    "disponibilidade",
    "duracao_job_s",
    "melibox_posicao",
    "melibox_tipo",
    "melibox_oferta_pct",
    "melibox_envio",
    "melibox_frete",
    "melibox_pagina",
]

HEADER_RENAMES = {
    "id_job": "job_id",
    "estado": "uf",
    "origem": "regiao",
}

DETALHADO_COLUMN_EXPRESSIONS: dict[str, str] = {
    "job_id": "={{ $json.job_id }}",
    "sku_pesquisado": "={{ $json.sku_searched }}",
    "sku_encontrado": "={{ $json.sku_found }}",
    "correspondencia_exata": "={{ $json.exact_match }}",
    "site": "={{ $json.site }}",
    "codigo_site": "={{ $json.site_code }}",
    "status_resultado": "={{ $json.status_resultado }}",
    "has_valid_price": "={{ $json.has_valid_price }}",
    "source_health": "={{ $json.source_health }}",
    "preco": "={{ $json.price }}",
    "preco-medio": "={{ $json.preco_medio }}",
    "moeda": "={{ $json.currency }}",
    "condicao": "={{ $json.condition }}",
    "vendedor": "={{ $json.seller }}",
    "uf": "={{ $json.uf }}",
    "empresa": "={{ $json.empresa }}",
    "cnpj": "={{ $json.cnpj }}",
    "url_produto": "={{ $json.product_url }}",
    "titulo_bruto": "={{ $json.raw_title }}",
    "marca": "={{ $json.brand }}",
    "regiao": "={{ $json.regiao }}",
    "coletado_em": "={{ $json.scraped_at }}",
    "tempo_busca_ms": "={{ $json.search_time_ms }}",
    "fonte_pipeline": "={{ $json.fonte_pipeline }}",
}

DETALHADO_COLUMN_ALIASES = {
    "id_job": "job_id",
    "estado": "uf",
    "origem": "regiao",
}

HISTORICO_EXTRA_COLUMNS = ["skus_not_found", "skus_blocked", "skus_error"]

RESUMO_EXTRA_COLUMNS = ["STATUS_RESULTADO"]

PAINEL_TAB = "Painel"

# Column letters for canonical Detalhado v2 (1-based A=1).
COL_SKU = "B"
COL_SITE = "E"
COL_STATUS = "G"
COL_HAS_PRICE = "H"
COL_SOURCE_HEALTH = "I"
COL_PRECO = "J"
COL_PIPELINE = "X"


def _rng(col: str) -> str:
    """Bounded Detalhado data range (avoids MAP/#ERROR on open-ended columns)."""
    return f"Detalhado!{col}2:INDEX(Detalhado!{col}:{col},COUNTA(Detalhado!A:A))"


_HAS_PRICE = f'REGEXMATCH(TO_TEXT({_rng(COL_HAS_PRICE)}),"(?i)^(true|1|sim)$")'
_SKU_OK = f'{_rng(COL_SKU)}<>"",{_rng(COL_SKU)}<>"SEM_DADOS"'
_FOUND_VALID = f'{_rng(COL_STATUS)}="FOUND_PRICE",{_HAS_PRICE}'

# Brazilian decimal strings (e.g. 30,81) and plain numbers.
_PARSED_PRICE = (
    f'MAP({_rng(COL_PRECO)},LAMBDA(p,IFERROR(IF(REGEXMATCH(TO_TEXT(p),","),'
    'VALUE(SUBSTITUTE(SUBSTITUTE(TO_TEXT(p),".",""),",",".")),'
    'IF(TO_TEXT(p)="","",VALUE(p))),0)))'
)

PAINEL_SITE_TABLE_FORMULA = (
    "=LET("
    f"skuR,{_rng(COL_SKU)},"
    f"siteR,{_rng(COL_SITE)},"
    f"statusR,{_rng(COL_STATUS)},"
    f"hasPriceR,{_HAS_PRICE},"
    f"parsedPrice,{_PARSED_PRICE},"
    f'sites,SORT(UNIQUE(FILTER(siteR,siteR<>""))),'
    "BYROW(sites,LAMBDA(s,HSTACK(s,"
    'COUNTUNIQUE(FILTER(skuR,(siteR=s)*(statusR="FOUND_PRICE")*hasPriceR*(skuR<>""))),'
    'COUNTUNIQUE(FILTER(skuR,(siteR=s)*(skuR<>"")*(skuR<>"SEM_DADOS"))),'
    'IFERROR(COUNTUNIQUE(FILTER(skuR,(siteR=s)*(statusR="FOUND_PRICE")*hasPriceR*(skuR<>"")))/COUNTUNIQUE(FILTER(skuR,(siteR=s)*(skuR<>"")*(skuR<>"SEM_DADOS"))),0),'
    "COUNTIF(siteR,s),"
    'IFERROR(MIN(FILTER(parsedPrice,(siteR=s)*(statusR="FOUND_PRICE")*hasPriceR*(parsedPrice>0))),0),'
    'IFERROR(AVERAGE(FILTER(parsedPrice,(siteR=s)*(statusR="FOUND_PRICE")*hasPriceR*(parsedPrice>0))),0),'
    'IFERROR(MAX(FILTER(parsedPrice,(siteR=s)*(statusR="FOUND_PRICE")*hasPriceR*(parsedPrice>0))),0)'
    ")))"
    ")"
)

PAINEL_SITE_TOTAL_ROW: list[str] = [
    "TOTAL",
    f"=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_FOUND_VALID})),0)",
    f"=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK})),0)",
    f"=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_FOUND_VALID}))/COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK})),0)",
    f'=IFERROR(COUNTA(FILTER({_rng(COL_SITE)},{_rng(COL_SITE)}<>"")),0)',
    f'=IFERROR(MIN(FILTER({_PARSED_PRICE},{_FOUND_VALID},{_PARSED_PRICE}>0)),"")',
    f'=IFERROR(AVERAGE(FILTER({_PARSED_PRICE},{_FOUND_VALID},{_PARSED_PRICE}>0)),"")',
    f'=IFERROR(MAX(FILTER({_PARSED_PRICE},{_FOUND_VALID},{_PARSED_PRICE}>0)),"")',
]

PAINEL_AVG_SITE_COVERAGE = (
    "=IFERROR(AVERAGE(MAP(SORT(UNIQUE(FILTER("
    f'{_rng(COL_SITE)},{_rng(COL_SITE)}<>""))),LAMBDA(s,IFERROR(COUNTUNIQUE(FILTER('
    f"{_rng(COL_SKU)},{_rng(COL_SITE)}=s,{_FOUND_VALID}))/COUNTUNIQUE(FILTER("
    f"{_rng(COL_SKU)},{_rng(COL_SITE)}=s,{_SKU_OK})),0)))),0)"
)

PAINEL_STATUS_ROWS: list[list[str]] = [
    [
        "✅  FOUND (preço válido)",
        f"=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_FOUND_VALID})),0)",
        f"=IFERROR(ROWS(FILTER({_rng(COL_STATUS)},{_FOUND_VALID})),0)",
        '=IFERROR(TEXT(B36/$A$5,"0.0%"),"—")',
    ],
    [
        "⚠️  SEM PREÇO (NO_PRICE)",
        f'=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_rng(COL_STATUS)}="NO_PRICE")),0)',
        f'=IFERROR(COUNTIF({_rng(COL_STATUS)},"NO_PRICE"),0)',
        '=IFERROR(TEXT(B37/$A$5,"0.0%"),"—")',
    ],
    [
        "❌  NÃO ENCONTRADO",
        f'=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_rng(COL_STATUS)}="NOT_FOUND")),0)',
        f'=IFERROR(COUNTIF({_rng(COL_STATUS)},"NOT_FOUND"),0)',
        '=IFERROR(TEXT(B38/$A$5,"0.0%"),"—")',
    ],
    [
        "🚫  BLOQUEADO",
        f'=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_rng(COL_STATUS)}="BLOCKED")),0)',
        f'=IFERROR(COUNTIF({_rng(COL_STATUS)},"BLOCKED"),0)',
        '=IFERROR(TEXT(B39/$A$5,"0.0%"),"—")',
    ],
    [
        "⏱️  TIMEOUT",
        f'=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_rng(COL_STATUS)}="TIMEOUT")),0)',
        f'=IFERROR(COUNTIF({_rng(COL_STATUS)},"TIMEOUT"),0)',
        '=IFERROR(TEXT(B40/$A$5,"0.0%"),"—")',
    ],
    [
        "💥  ERRO",
        f'=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_rng(COL_STATUS)}="ERROR")),0)',
        f'=IFERROR(COUNTIF({_rng(COL_STATUS)},"ERROR"),0)',
        '=IFERROR(TEXT(B41/$A$5,"0.0%"),"—")',
    ],
    [
        "⏸️  NÃO CONSULTADO",
        f'=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_rng(COL_STATUS)}="NOT_QUERIED")),0)',
        f'=IFERROR(COUNTIF({_rng(COL_STATUS)},"NOT_QUERIED"),0)',
        '=IFERROR(TEXT(B42/$A$5,"0.0%"),"—")',
    ],
]

PAINEL_PIPELINE_ROWS: list[list[str]] = [
    [
        "API Diversos",
        f'=IFERROR(COUNTIF({_rng(COL_PIPELINE)},"API Diversos"),0)',
        f'=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_rng(COL_PIPELINE)}="API Diversos",{_FOUND_VALID})),0)',
        '=IFERROR(TEXT(C46/B46,"0.0%"),"—")',
    ],
    [
        "WEBSCRAPER",
        f'=IFERROR(COUNTIF({_rng(COL_PIPELINE)},"WEBSCRAPER"),0)',
        f'=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_rng(COL_PIPELINE)}="WEBSCRAPER",{_FOUND_VALID})),0)',
        '=IFERROR(TEXT(C47/B47,"0.0%"),"—")',
    ],
]

PAINEL_JOBS_FORMULA = '=IFERROR(QUERY(Historico!A2:J,"select B,G,H,J,F where A is not null order by E desc limit 5",0),"—")'

PAINEL_UPDATES: list[tuple[str, list[list[str]]]] = [
    (
        "A1:H2",
        [
            ["🔍  PAINEL — CDP RESULTADOS", "", "", "", "", "", "", ""],
            [
                '=IFERROR("Atualizado automaticamente | "&TEXT(INDEX(Historico!E:E,COUNTA(Historico!E:E)),"DD/MM/YYYY HH:MM")&" | KPIs por FOUND_PRICE + has_valid_price","—")',
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ],
    ),
    (
        "A4:H11",
        [
            [
                "🗂️  TOTAL SKUs PESQUISADOS",
                "",
                "✅  SKUs COM PREÇO",
                "",
                "❌  SEM PREÇO / BLOQUEIO / ERRO",
                "",
                "⏱️  DURAÇÃO",
                "",
            ],
            [
                f"=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK})),0)",
                "",
                f"=IFERROR(COUNTUNIQUE(FILTER({_rng(COL_SKU)},{_SKU_OK},{_FOUND_VALID})),0)",
                "",
                "=MAX(A5-C5,0)",
                "",
                "=IFERROR(ROUND(VALUE(INDEX(Historico!F:F,COUNTA(Historico!F:F)))/60,1),0)",
                "",
            ],
            [
                "SKUs únicos",
                "",
                "FOUND_PRICE + preço válido",
                "",
                "demais status canônicos",
                "",
                "minutos (último job)",
                "",
            ],
            [
                '=IFERROR("Jobs: "&(COUNTA(Historico!A:A)-1)&"   |   Último: "&INDEX(Historico!B:B,COUNTA(Historico!B:B)),"—")',
                "",
                '=IFERROR(TEXT(C5/A5,"0.0%")&" com preço","—")',
                "",
                '=IFERROR(TEXT(E5/A5,"0.0%")&" sem preço válido","—")',
                "",
                '=IFERROR(TEXT(SUM(FILTER(Historico!F2:F,Historico!F2:F<>""))/3600,"0.0")&"h total","—")',
                "",
            ],
            [
                "📊  TAXA SUCESSO SKU",
                "",
                "🎯  % COBERTURA POR SITE",
                "",
                "🌐  SITES",
                "",
                "📋  JOBS TOTAL",
                "",
            ],
            [
                '=IFERROR(TEXT(C5/A5,"0.0%"),"—")',
                "",
                f"={PAINEL_AVG_SITE_COVERAGE.lstrip('=')}",
                "",
                f'=IFERROR(COUNTA(UNIQUE(FILTER({_rng(COL_SITE)},{_rng(COL_SITE)}<>""))),0)',
                "",
                "=IFERROR(COUNTA(Historico!A:A)-1,0)",
                "",
            ],
            [
                "via Detalhado canônico",
                "",
                "média de cobertura por site",
                "",
                "sites no Detalhado",
                "",
                "jobs no histórico",
                "",
            ],
            [
                '=IFERROR("🔗  Job: "&INDEX(Historico!A:A,COUNTA(Historico!A:A))&"   |   Status: "&INDEX(Historico!G:G,COUNTA(Historico!G:G))&"   |   SKUs Lidos: "&INDEX(Historico!H:H,COUNTA(Historico!H:H))&"   |   Origem: "&INDEX(Historico!B:B,COUNTA(Historico!B:B)),"—")',
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ],
    ),
    (
        "A12:H12",
        [["", "", "", "", "", "", "", ""]],
    ),
    (
        "A14:H16",
        [
            [
                "📡  COBERTURA POR SITE — FOUND_PRICE + has_valid_price (via Detalhado)",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
            [
                "Site",
                "SKUs c/ Preço",
                "Total SKUs",
                "% Cobertura",
                "Linhas Detalhado",
                "Preço Mín (R$)",
                "Preço Médio (R$)",
                "Preço Máx (R$)",
            ],
            [PAINEL_SITE_TABLE_FORMULA, "", "", "", "", "", "", ""],
        ],
    ),
    (
        "A27:H27",
        [PAINEL_SITE_TOTAL_ROW],
    ),
    (
        "A34:D35",
        [
            ["📊  DISTRIBUIÇÃO POR STATUS (SKUs únicos vs linhas Detalhado)", "", "", ""],
            ["Status", "SKUs únicos", "Linhas Detalhado", "% dos SKUs"],
        ],
    ),
    (
        "A36:D42",
        PAINEL_STATUS_ROWS,
    ),
    (
        "A44:D45",
        [
            ["🔌  FONTE PIPELINE (linhas vs SKUs com preço)", "", "", ""],
            ["Fonte", "Linhas", "SKUs c/ Preço", "% linhas c/ preço"],
        ],
    ),
    (
        "A46:D47",
        PAINEL_PIPELINE_ROWS,
    ),
    (
        "A49:E50",
        [
            ["📋  ÚLTIMOS JOBS (Historico)", "", "", "", ""],
            ["Origem", "Status", "SKUs Lidos", "SKUs c/ Preço", "Duração (s)"],
        ],
    ),
    (
        "A51:E51",
        [[PAINEL_JOBS_FORMULA, "", "", "", ""]],
    ),
]

# Stale static rows below site-table spill (dynamic from A16; TOTAL lives at A27).
PAINEL_CLEAR_RANGE = "A17:H26"


def fonte_pipeline_from_row(row: dict[str, str]) -> str:
    code = str(row.get("codigo_site") or row.get("site_code") or "").strip().lower()
    if code in {"api-diversos", "muvstok"}:
        return "API Diversos"
    return "WEBSCRAPER"


def clean_detalhado_row(row: dict[str, str]) -> dict[str, str]:
    """Normalize one Detalhado data row for v2 schema."""
    out = dict(row)

    if "regiao" not in out and out.get("origem"):
        out["regiao"] = out["origem"]
    out.pop("origem", None)
    out.pop("disponibilidade", None)
    out.pop("duracao_job_s", None)

    out["fonte_pipeline"] = fonte_pipeline_from_row(out)

    vendedor = str(out.get("vendedor") or "").strip()
    empresa = str(out.get("empresa") or "").strip()
    if not empresa or empresa in {"N/A", "NA"} or empresa == vendedor:
        out["empresa"] = ""

    status = str(out.get("status_resultado") or "").strip().upper()
    title = str(out.get("titulo_bruto") or "").strip()
    diagnostic_prefixes = ("NOT_FOUND", "BLOQUEADO:", "TIMEOUT:", "ERRO:", "SEM_PRECO:")
    if status in {"NOT_FOUND", "BLOCKED", "TIMEOUT", "ERROR", "NOT_QUERIED"} or any(
        title.startswith(p) for p in diagnostic_prefixes
    ):
        out["titulo_bruto"] = ""

    return out


def remap_row_to_headers(row: dict[str, str], headers: list[str]) -> list[str]:
    cleaned = clean_detalhado_row(row)
    return [str(cleaned.get(h, "") or "") for h in headers]
