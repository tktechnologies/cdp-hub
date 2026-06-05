#!/usr/bin/env python3
"""Ensure cdp_resultados Detalhado tab has required canonical result headers.

Requires: pip install google-api-python-client google-auth
Auth: GOOGLE_APPLICATION_CREDENTIALS

Usage:
  uv run --with google-api-python-client --with google-auth \
    python scripts/ensure_google_sheets_schema.py --dry-run
  uv run --with google-api-python-client --with google-auth \
    python scripts/ensure_google_sheets_schema.py
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

SPREADSHEET_ID = "1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo"
# Detalhado tab gid from production sheet URL (user link).
DETALHADO_GID = 533358674

DETALHADO_COLUMNS_AFTER_PRECO = ["preco-medio"]
DETALHADO_COLUMNS_AFTER_VENDEDOR = ["uf", "empresa", "cnpj", "url_produto"]
DETALHADO_COLUMNS_AFTER_CODIGO_SITE = [
    "status_resultado",
    "source_health",
    "has_valid_price",
]
DETALHADO_COLUMNS_REMOVE = [
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
}


def resolve_sheet(sheet_api: Any, spreadsheet_id: str, gid: int | None) -> tuple[str, int | None]:
    """Resolve tab title and numeric sheetId by gid, or default to Detalhado."""
    if gid is None:
        return "Detalhado", None
    meta = (
        sheet_api.get(spreadsheetId=spreadsheet_id, fields="sheets.properties")
        .execute()
        .get("sheets", [])
    )
    for sheet in meta:
        props = sheet.get("properties", {})
        if props.get("sheetId") == gid:
            return str(props.get("title", "Detalhado")), int(gid)
    raise SystemExit(f"No tab with gid={gid} in spreadsheet {spreadsheet_id}")


def migrate_headers(headers: list[str]) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """Return migrated headers, insert operations, and human-readable rename notes."""
    out = list(headers)
    notes: list[str] = []
    operations: list[dict[str, Any]] = []

    for column in DETALHADO_COLUMNS_REMOVE:
        while column in out:
            start_index = out.index(column)
            out.pop(start_index)
            operations.append({"type": "delete", "start_index": start_index, "count": 1, "headers": [column]})
            notes.append(f"delete `{column}`")

    for old, new in HEADER_RENAMES.items():
        if old in out and new not in out:
            out[out.index(old)] = new
            notes.append(f"rename `{old}` -> `{new}`")
        elif old in out and new in out:
            legacy = f"{old}_legacy"
            suffix = 2
            while legacy in out:
                legacy = f"{old}_legacy_{suffix}"
                suffix += 1
            out[out.index(old)] = legacy
            notes.append(f"rename duplicate legacy `{old}` -> `{legacy}`")

    def ensure_sequence_after(anchor: str, required: list[str]) -> None:
        if anchor not in out:
            raise SystemExit(f"Column `{anchor}` not found in Detalhado row 1.")
        previous = anchor
        for column in required:
            if column in out:
                previous = column
                continue
            insert_at = out.index(previous) + 1
            out.insert(insert_at, column)
            operations.append({"type": "insert", "start_index": insert_at, "count": 1, "headers": [column]})
            previous = column

    ensure_sequence_after("preco", DETALHADO_COLUMNS_AFTER_PRECO)
    ensure_sequence_after("vendedor", DETALHADO_COLUMNS_AFTER_VENDEDOR)
    ensure_sequence_after("codigo_site", DETALHADO_COLUMNS_AFTER_CODIGO_SITE)

    return out, operations, notes


def apply_column_changes(
    sheet_api: Any,
    spreadsheet_id: str,
    sheet_id: int,
    operations: list[dict[str, Any]],
) -> None:
    requests = []
    delete_ops = [op for op in operations if op.get("type") == "delete"]
    insert_ops = [op for op in operations if op.get("type") == "insert"]
    for op in sorted(delete_ops, key=lambda item: int(item["start_index"]), reverse=True):
        start = int(op["start_index"])
        count = int(op["count"])
        requests.append(
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": start,
                        "endIndex": start + count,
                    },
                }
            }
        )
    for op in insert_ops:
        start = int(op["start_index"])
        count = int(op["count"])
        requests.append(
            {
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": start,
                        "endIndex": start + count,
                    },
                    "inheritFromBefore": True,
                }
            }
        )
    if requests:
        sheet_api.batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--spreadsheet-id", default=SPREADSHEET_ID)
    parser.add_argument(
        "--gid",
        type=int,
        default=DETALHADO_GID,
        help=f"Sheet gid for Detalhado tab (default {DETALHADO_GID})",
    )
    parser.add_argument(
        "--tab",
        default="",
        help="Tab name override (default: resolve from --gid)",
    )
    args = parser.parse_args()

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.isfile(creds_path):
        print(
            "Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON with edit access.\n"
            "Manual alternative: add `preco-medio` after `preco`, "
            "`uf`/`empresa`/`cnpj` after `vendedor`, remove `melibox_*`, "
            "and add canonical status headers after `codigo_site`.",
            file=sys.stderr,
        )
        return 1

    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError:
        print("Install: pip install google-api-python-client google-auth", file=sys.stderr)
        return 1

    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sheet_api = service.spreadsheets()

    tab_name, sheet_id = (
        (args.tab.strip(), args.gid)
        if args.tab.strip()
        else resolve_sheet(sheet_api, args.spreadsheet_id, args.gid)
    )
    print(f"Target tab: {tab_name!r} (gid={args.gid})")

    header_row = (
        sheet_api.values()
        .get(spreadsheetId=args.spreadsheet_id, range=f"'{tab_name}'!1:1")
        .execute()
        .get("values")
        or [[]]
    )[0]
    headers = [str(h).strip() for h in header_row]

    new_headers, operations, notes = migrate_headers(headers)
    if new_headers == headers:
        print(f"{tab_name} headers OK:", ", ".join(headers))
        return 0

    for op in operations:
        cols = ", ".join(f"`{h}`" for h in op["headers"])
        if op.get("type") == "insert":
            notes.append(f"insert {cols} at 1-based column {int(op['start_index']) + 1}")
    for note in notes:
        print("-", note)
    print(f"Will set {tab_name} row 1 to:", new_headers)

    if args.dry_run:
        print("(dry-run, no changes written)")
        return 0

    if operations:
        if sheet_id is None:
            raise SystemExit("Sheet gid is required to insert columns safely.")
        apply_column_changes(sheet_api, args.spreadsheet_id, int(sheet_id), operations)

    sheet_api.values().update(
        spreadsheetId=args.spreadsheet_id,
        range=f"'{tab_name}'!1:1",
        valueInputOption="RAW",
        body={"values": [new_headers]},
    ).execute()
    print(f"Updated {tab_name} header row.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
