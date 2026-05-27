#!/usr/bin/env python3
"""Ensure cdp_resultados Detalhado tab has required column headers (e.g. preco-medio).

Requires: pip install google-api-python-client google-auth
Auth: GOOGLE_APPLICATION_CREDENTIALS

Usage:
  python3 scripts/ensure_google_sheets_schema.py --dry-run
  python3 scripts/ensure_google_sheets_schema.py
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

SPREADSHEET_ID = "1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo"
# Detalhado tab gid from production sheet URL (user link).
DETALHADO_GID = 533358674

# Columns to insert after `preco` when missing (header name).
DETALHADO_COLUMNS_AFTER_PRECO = ["preco-medio"]


def resolve_sheet_title(sheet_api: Any, spreadsheet_id: str, gid: int | None) -> str:
    """Resolve tab title by gid or default to Detalhado."""
    if gid is None:
        return "Detalhado"
    meta = (
        sheet_api.get(spreadsheetId=spreadsheet_id, fields="sheets.properties")
        .execute()
        .get("sheets", [])
    )
    for sheet in meta:
        props = sheet.get("properties", {})
        if props.get("sheetId") == gid:
            return str(props.get("title", "Detalhado"))
    raise SystemExit(f"No tab with gid={gid} in spreadsheet {spreadsheet_id}")


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

    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError:
        print("Install: pip install google-api-python-client google-auth", file=sys.stderr)
        return 1

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.isfile(creds_path):
        print(
            "Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON with edit access.\n"
            "Manual alternative: add column header `preco-medio` on Detalhado after `preco`.",
            file=sys.stderr,
        )
        return 1

    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sheet_api = service.spreadsheets()

    tab_name = args.tab.strip() or resolve_sheet_title(sheet_api, args.spreadsheet_id, args.gid)
    print(f"Target tab: {tab_name!r} (gid={args.gid})")

    header_row = (
        sheet_api.values()
        .get(spreadsheetId=args.spreadsheet_id, range=f"'{tab_name}'!1:1")
        .execute()
        .get("values")
        or [[]]
    )[0]
    headers = [str(h).strip() for h in header_row]

    missing = [c for c in DETALHADO_COLUMNS_AFTER_PRECO if c not in headers]
    if not missing:
        print(f"{tab_name} headers OK:", ", ".join(headers))
        return 0

    if "preco" not in headers:
        print(f"Column `preco` not found in {tab_name} row 1 — add headers manually.", file=sys.stderr)
        return 1

    insert_at = headers.index("preco") + 1
    new_headers = headers[:insert_at] + missing + headers[insert_at:]
    print(f"Will set {tab_name} row 1 to:", new_headers)

    if args.dry_run:
        print("(dry-run, no changes written)")
        return 0

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
