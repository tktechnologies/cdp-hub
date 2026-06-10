#!/usr/bin/env python3
"""Apply Google Sheets audit: Detalhado v2 schema, Painel formulas, data cleanup.

Auth (first match):
  1. GOOGLE_APPLICATION_CREDENTIALS → service account JSON
  2. GOOGLE_APPLICATION_CREDENTIAL_ID + GOOGLE_APPLICATION_CREDENTIAL_KEY → OAuth token cache

Usage:
  cd muvstok-api
  uv run --with google-api-python-client --with google-auth --with google-auth-oauthlib \
    python scripts/apply_google_sheets_audit.py --dry-run
  uv run --with google-api-python-client --with google-auth --with google-auth-oauthlib \
    python scripts/apply_google_sheets_audit.py
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from google_sheets_audit_schema import (  # noqa: E402
    CANONICAL_DETALHADO_HEADERS,
    DETALHADO_GID,
    HEADER_RENAMES,
    PAINEL_CLEAR_RANGE,
    PAINEL_TAB,
    PAINEL_UPDATES,
    SPREADSHEET_ID,
    remap_row_to_headers,
)

REPO_ROOT = SCRIPT_DIR.parents[1]
TOKEN_PATH = REPO_ROOT / ".credentials" / "google-sheets-token.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def load_dotenv() -> None:
    for path in (REPO_ROOT / ".env", SCRIPT_DIR.parent / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def get_credentials():
    from google.auth.transport.requests import Request  # type: ignore

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if creds_path and os.path.isfile(creds_path):
        from google.oauth2 import service_account  # type: ignore

        return service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    client_id = os.environ.get("GOOGLE_APPLICATION_CREDENTIAL_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_APPLICATION_CREDENTIAL_KEY", "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "Set GOOGLE_APPLICATION_CREDENTIALS (service account) or "
            "GOOGLE_APPLICATION_CREDENTIAL_ID + GOOGLE_APPLICATION_CREDENTIAL_KEY in .env"
        )

    from google.oauth2.credentials import Credentials  # type: ignore
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore

    oauth_code = os.environ.get("GOOGLE_OAUTH_CODE", "").strip()
    creds = None
    if TOKEN_PATH.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if oauth_code:
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            SCOPES,
        )
        flow.fetch_token(code=oauth_code)
        creds = flow.credentials
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            SCOPES,
        )
        try:
            creds = flow.run_local_server(port=0, open_browser=False, timeout_seconds=60)
        except Exception as exc:
            auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
            raise SystemExit(
                "OAuth required. Open this URL, authorize, then re-run with GOOGLE_OAUTH_CODE set:\n"
                f"{auth_url}\n"
                f"(local server failed: {exc})"
            ) from exc
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_sheets_service(creds: Any) -> Any:
    from googleapiclient.discovery import build  # type: ignore

    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def resolve_sheet(sheet_api: Any, spreadsheet_id: str, gid: int) -> tuple[str, int]:
    meta = sheet_api.get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("sheetId") == gid:
            return str(props.get("title", "Detalhado")), int(gid)
    raise SystemExit(f"No tab with gid={gid}")


def fetch_public_csv(spreadsheet_id: str, gid: int) -> list[dict[str, str]]:
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export"
        f"?format=csv&gid={gid}"
    )
    with urllib.request.urlopen(url, timeout=120) as resp:
        text = resp.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def migrate_detalhado(
    sheet_api: Any,
    spreadsheet_id: str,
    tab_name: str,
    *,
    dry_run: bool,
) -> None:
    print(f"Migrating Detalhado tab {tab_name!r} → v2 ({len(CANONICAL_DETALHADO_HEADERS)} columns)")

    result = (
        sheet_api.values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A:ZZ")
        .execute()
    )
    values = result.get("values") or []
    if not values:
        print("Detalhado is empty; setting headers only.")
        data_rows: list[list[str]] = []
    else:
        headers = [str(h).strip() for h in values[0]]
        renamed = [HEADER_RENAMES.get(h, h) for h in headers]
        data_rows = []
        for raw in values[1:]:
            row_dict = {
                renamed[i]: raw[i] if i < len(raw) else ""
                for i in range(len(renamed))
            }
            data_rows.append(remap_row_to_headers(row_dict, CANONICAL_DETALHADO_HEADERS))

    out_values = [CANONICAL_DETALHADO_HEADERS, *data_rows]
    print(f"- rewrite {len(data_rows)} data rows")
    if dry_run:
        return

    sheet_api.values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A:ZZ",
        body={},
    ).execute()
    sheet_api.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A1",
        valueInputOption="RAW",
        body={"values": out_values},
    ).execute()
    print("Detalhado migrated.")


def apply_painel(sheet_api: Any, spreadsheet_id: str, *, dry_run: bool) -> None:
    print(f"Refreshing {PAINEL_TAB} formulas (Detalhado v2 column letters).")
    for range_suffix, block in PAINEL_UPDATES:
        print(f"- {PAINEL_TAB}!{range_suffix}")
        if dry_run:
            continue
        sheet_api.values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{PAINEL_TAB}'!{range_suffix}",
            valueInputOption="USER_ENTERED",
            body={"values": block},
        ).execute()
    if not dry_run:
        sheet_api.values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{PAINEL_TAB}'!{PAINEL_CLEAR_RANGE}",
            body={},
        ).execute()
    print(f"{PAINEL_TAB} updated.")


def ensure_historico_headers(sheet_api: Any, spreadsheet_id: str, *, dry_run: bool) -> None:
    extra = ["skus_not_found", "skus_blocked", "skus_error"]
    header_row = (
        sheet_api.values()
        .get(spreadsheetId=spreadsheet_id, range="'Historico'!1:1")
        .execute()
        .get("values")
        or [[]]
    )[0]
    headers = [str(h).strip() for h in header_row]
    missing = [c for c in extra if c not in headers]
    if not missing:
        print("Historico headers OK.")
        return
    new_headers = headers + missing
    print(f"Historico: append columns {missing}")
    if dry_run:
        return
    sheet_api.values().update(
        spreadsheetId=spreadsheet_id,
        range="'Historico'!1:1",
        valueInputOption="RAW",
        body={"values": [new_headers]},
    ).execute()


def ensure_resumo_headers(sheet_api: Any, spreadsheet_id: str, *, dry_run: bool) -> None:
    extra = ["STATUS_RESULTADO"]
    header_row = (
        sheet_api.values()
        .get(spreadsheetId=spreadsheet_id, range="'Resumo'!1:1")
        .execute()
        .get("values")
        or [[]]
    )[0]
    headers = [str(h).strip() for h in header_row]
    if "STATUS_RESULTADO" in headers:
        print("Resumo headers OK.")
        return
    # Insert after STATUS if present
    if "STATUS" in headers:
        idx = headers.index("STATUS") + 1
        new_headers = headers[:idx] + extra + headers[idx:]
    else:
        new_headers = headers + extra
    print("Resumo: add STATUS_RESULTADO column")
    if dry_run:
        return
    sheet_api.values().update(
        spreadsheetId=spreadsheet_id,
        range="'Resumo'!1:1",
        valueInputOption="RAW",
        body={"values": [new_headers]},
    ).execute()


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Apply CDP Google Sheets audit")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--spreadsheet-id", default=SPREADSHEET_ID)
    parser.add_argument("--gid", type=int, default=DETALHADO_GID)
    parser.add_argument("--skip-detalhado", action="store_true")
    parser.add_argument("--skip-painel", action="store_true")
    parser.add_argument("--skip-historico", action="store_true")
    parser.add_argument("--skip-resumo", action="store_true")
    args = parser.parse_args()

    try:
        from googleapiclient.discovery import build  # type: ignore  # noqa: F401
    except ImportError:
        print(
            "Install: uv run --with google-api-python-client --with google-auth "
            "--with google-auth-oauthlib python scripts/apply_google_sheets_audit.py",
            file=sys.stderr,
        )
        return 1

    creds = get_credentials()
    sheet_api = build_sheets_service(creds).spreadsheets()
    tab_name, _ = resolve_sheet(sheet_api, args.spreadsheet_id, args.gid)
    print(f"Spreadsheet {args.spreadsheet_id} | Detalhado gid={args.gid} tab={tab_name!r}")

    if not args.skip_detalhado:
        migrate_detalhado(sheet_api, args.spreadsheet_id, tab_name, dry_run=args.dry_run)
    if not args.skip_painel:
        apply_painel(sheet_api, args.spreadsheet_id, dry_run=args.dry_run)
    if not args.skip_historico:
        ensure_historico_headers(sheet_api, args.spreadsheet_id, dry_run=args.dry_run)
    if not args.skip_resumo:
        ensure_resumo_headers(sheet_api, args.spreadsheet_id, dry_run=args.dry_run)

    if args.dry_run:
        print("(dry-run — no writes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
