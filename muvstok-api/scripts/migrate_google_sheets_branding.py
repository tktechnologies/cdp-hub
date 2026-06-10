#!/usr/bin/env python3
"""Rewrite legacy 'muvstok' labels to API Diversos in cdp_resultados Google Sheet.

Requires: pip install google-api-python-client google-auth
Auth: GOOGLE_APPLICATION_CREDENTIALS pointing at a service account with edit access.

Usage:
  python3 scripts/migrate_google_sheets_branding.py --dry-run
  python3 scripts/migrate_google_sheets_branding.py
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

SPREADSHEET_ID = "1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo"

TAB_COLUMNS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "Detalhado": {
        "site": [("muvstok", "API Diversos"), ("Muvstok", "API Diversos")],
        "codigo_site": [("muvstok", "api-diversos"), ("Muvstok", "api-diversos")],
    },
    "Historico": {
        "origem": [("muvstok", "API Diversos"), ("Muvstok", "API Diversos")],
    },
    "Resumo": {
        "SITE": [("muvstok", "API Diversos"), ("Muvstok", "API Diversos")],
    },
}


def _replace_cell(value: str, rules: list[tuple[str, str]]) -> str:
    out = value
    for old, new in rules:
        if old in out:
            out = out.replace(old, new)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--spreadsheet-id", default=SPREADSHEET_ID)
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
            "Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON with edit access "
            "to the spreadsheet, then re-run.\n"
            "Manual alternative: in cdp_resultados, Find/Replace muvstok → API Diversos "
            "(site, origem, SITE) and codigo_site muvstok → api-diversos.",
            file=sys.stderr,
        )
        return 1

    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sheet_api = service.spreadsheets()

    total_updates = 0
    for tab_name, col_rules in TAB_COLUMNS.items():
        header_row = (
            sheet_api.values()
            .get(spreadsheetId=args.spreadsheet_id, range=f"'{tab_name}'!1:1")
            .execute()
            .get("values")
            or [[]]
        )[0]
        col_index = {str(h).strip(): i for i, h in enumerate(header_row)}

        data = (
            sheet_api.values()
            .get(spreadsheetId=args.spreadsheet_id, range=f"'{tab_name}'!A2:ZZ")
            .execute()
            .get("values")
            or []
        )
        if not data:
            print(f"{tab_name}: no data rows")
            continue

        out_rows: list[list[Any]] = []
        changed = 0
        for row in data:
            padded = list(row) + [""] * max(0, len(header_row) - len(row))
            row_changed = False
            for col_name, rules in col_rules.items():
                idx = col_index.get(col_name)
                if idx is None:
                    continue
                old = str(padded[idx]) if idx < len(padded) else ""
                new = _replace_cell(old, rules)
                if new != old:
                    padded[idx] = new
                    row_changed = True
            out_rows.append(padded)
            if row_changed:
                changed += 1

        if not changed:
            print(f"{tab_name}: nothing to change")
            continue

        print(f"{tab_name}: {changed} row(s)" + (" (dry-run)" if args.dry_run else " updated"))
        total_updates += changed

        if args.dry_run:
            continue

        sheet_api.values().update(
            spreadsheetId=args.spreadsheet_id,
            range=f"'{tab_name}'!A2",
            valueInputOption="RAW",
            body={"values": out_rows},
        ).execute()

    print(f"Done. Rows touched: {total_updates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
