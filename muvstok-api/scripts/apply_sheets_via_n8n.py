#!/usr/bin/env python3
"""Apply Google Sheets audit via one-shot n8n workflow (uses live Sheets OAuth in n8n)."""

from __future__ import annotations

import csv
import io
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_audit_schema import (  # noqa: E402
    CANONICAL_DETALHADO_HEADERS,
    PAINEL_CLEAR_RANGE,
    PAINEL_TAB,
    PAINEL_UPDATES,
    SPREADSHEET_ID,
    remap_row_to_headers,
)
from n8n_publish import (  # noqa: E402
    activate_via_rest,
    deactivate_via_rest,
    n8n_api_base,
    n8n_api_key,
    n8n_api_request,
)

SHEET_ID = SPREADSHEET_ID
DETALHADO_GID = 1185876304
WEBHOOK_PATH = "cdp-sheets-audit-apply"
SHEETS_CRED = {
    "googleSheetsOAuth2Api": {"id": "ep05fPlF3xggWhWc", "name": "gcp sheets lucas@tktech"}
}


def load_dotenv() -> None:
    for path in (REPO_ROOT / ".env", SCRIPT_DIR.parent / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            import os

            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def fetch_detalhado_rows() -> list[list[str]]:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={DETALHADO_GID}"
    with urllib.request.urlopen(url, timeout=120) as resp:
        raw = resp.read().decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(raw)))
    return [CANONICAL_DETALHADO_HEADERS] + [
        remap_row_to_headers(row, CANONICAL_DETALHADO_HEADERS) for row in rows
    ]


def fetch_header_row(gid: int) -> list[str]:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        first = resp.read().decode("utf-8-sig").splitlines()[0]
    return next(csv.reader(io.StringIO(first)))


def extend_headers(
    tab: str, gid: int, extra: list[str], after: str | None = None
) -> list[str] | None:
    headers = [str(h).strip() for h in fetch_header_row(gid)]
    missing = [c for c in extra if c not in headers]
    if not missing:
        return None
    if after and after in headers:
        idx = headers.index(after) + 1
        return headers[:idx] + missing + headers[idx:]
    return headers + missing


def painel_batch_body() -> dict:
    data = []
    for range_suffix, block in PAINEL_UPDATES:
        tab_range = f"Painel!{range_suffix}"
        data.append({"range": tab_range, "values": block})
    return {"valueInputOption": "USER_ENTERED", "data": data}


def build_workflow(
    values: list[list[str]],
    painel_batch: dict,
    *,
    historico_headers: list[str] | None,
    resumo_headers: list[str] | None,
) -> dict:
    values_json = json.dumps(values, ensure_ascii=False)
    painel_json = json.dumps(painel_batch, ensure_ascii=False)
    extra = {
        "historicoHeaders": historico_headers,
        "resumoHeaders": resumo_headers,
    }
    extra_json = json.dumps(extra, ensure_ascii=False)
    code = f"""const values = {values_json};
const painelBatch = {painel_json};
const extra = {extra_json};
return [{{ json: {{ values, painelBatch, ...extra }} }}];"""

    nodes = [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": WEBHOOK_PATH,
                "responseMode": "lastNode",
                "options": {},
            },
            "id": "wh-1",
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [0, 0],
            "webhookId": "cdp-sheets-audit",
        },
        {
            "parameters": {"jsCode": code},
            "id": "code-1",
            "name": "Load migration payload",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [220, 0],
        },
        {
            "parameters": {
                "method": "POST",
                "url": f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Detalhado'!A:ZZ:clear",
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googleSheetsOAuth2Api",
                "options": {},
            },
            "id": "http-clear",
            "name": "Clear Detalhado",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [440, 0],
            "credentials": SHEETS_CRED,
        },
        {
            "parameters": {
                "method": "PUT",
                "url": f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Detalhado'!A1?valueInputOption=RAW",
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googleSheetsOAuth2Api",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify({ values: $('Load migration payload').first().json.values }) }}",
                "options": {},
            },
            "id": "http-update",
            "name": "Write Detalhado v2",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [660, 0],
            "credentials": SHEETS_CRED,
        },
        {
            "parameters": {
                "method": "POST",
                "url": f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate",
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googleSheetsOAuth2Api",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($('Load migration payload').first().json.painelBatch) }}",
                "options": {},
            },
            "id": "http-painel",
            "name": "Refresh Painel",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [880, 0],
            "credentials": SHEETS_CRED,
        },
        {
            "parameters": {
                "method": "POST",
                "url": (
                    f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/"
                    f"'{PAINEL_TAB}'!{PAINEL_CLEAR_RANGE}:clear"
                ),
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googleSheetsOAuth2Api",
                "options": {},
            },
            "id": "http-painel-clear",
            "name": "Clear stale Painel rows",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1100, 0],
            "credentials": SHEETS_CRED,
        },
    ]
    connections: dict = {
        "Webhook": {"main": [[{"node": "Load migration payload", "type": "main", "index": 0}]]},
        "Load migration payload": {
            "main": [[{"node": "Clear Detalhado", "type": "main", "index": 0}]]
        },
        "Clear Detalhado": {"main": [[{"node": "Write Detalhado v2", "type": "main", "index": 0}]]},
        "Write Detalhado v2": {"main": [[{"node": "Refresh Painel", "type": "main", "index": 0}]]},
        "Refresh Painel": {
            "main": [[{"node": "Clear stale Painel rows", "type": "main", "index": 0}]]
        },
    }
    last = "Clear stale Painel rows"
    x = 1320
    if historico_headers:
        nodes.append(
            {
                "parameters": {
                    "method": "PUT",
                    "url": f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Historico'!1:1?valueInputOption=RAW",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "googleSheetsOAuth2Api",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ values: [$('Load migration payload').first().json.historicoHeaders] }) }}",
                    "options": {},
                },
                "id": "http-hist",
                "name": "Historico headers",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [x, 0],
                "credentials": SHEETS_CRED,
            }
        )
        connections[last] = {"main": [[{"node": "Historico headers", "type": "main", "index": 0}]]}
        last = "Historico headers"
        x += 220
    if resumo_headers:
        nodes.append(
            {
                "parameters": {
                    "method": "PUT",
                    "url": f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Resumo'!1:1?valueInputOption=RAW",
                    "authentication": "predefinedCredentialType",
                    "nodeCredentialType": "googleSheetsOAuth2Api",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ values: [$('Load migration payload').first().json.resumoHeaders] }) }}",
                    "options": {},
                },
                "id": "http-resumo",
                "name": "Resumo headers",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [x, 0],
                "credentials": SHEETS_CRED,
            }
        )
        connections[last] = {"main": [[{"node": "Resumo headers", "type": "main", "index": 0}]]}
    return {
        "name": "MAINT cdp_sheets_audit_apply",
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
    }


def trigger_webhook() -> None:
    base = n8n_api_base().replace("/api/v1", "")
    url = f"{base}/webhook/{WEBHOOK_PATH}"
    req = urllib.request.Request(
        url, data=b"{}", method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        print("webhook", resp.status, resp.read()[:200])


def wait_execution(workflow_id: str, timeout_s: int = 120) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        data = n8n_api_request("GET", f"/executions?workflowId={workflow_id}&limit=1")
        items = data.get("data") or []
        if items:
            ex = items[0]
            status = ex.get("status")
            if status in {"success", "error", "crashed"}:
                return status
        time.sleep(2)
    return "timeout"


def main() -> int:
    load_dotenv()
    if not n8n_api_key():
        print("Missing N8N_API_KEY", file=sys.stderr)
        return 1

    print("Fetching and transforming Detalhado export…")
    values = fetch_detalhado_rows()
    print(f"Prepared {len(values) - 1} data rows + header")

    historico_headers = extend_headers(
        "Historico", 79112561, ["skus_not_found", "skus_blocked", "skus_error"], after="skus_falhos"
    )
    resumo_headers = None
    for gid in (79112561, 1185876304, *range(1, 30)):
        try:
            h = fetch_header_row(gid)
        except Exception:
            continue
        if h and str(h[0]).strip() == "CODIGO":
            resumo_headers = extend_headers("Resumo", gid, ["STATUS_RESULTADO"], after="STATUS")
            break
    wf_body = build_workflow(
        values,
        painel_batch_body(),
        historico_headers=historico_headers,
        resumo_headers=resumo_headers,
    )
    wf_id = None
    try:
        created = n8n_api_request("POST", "/workflows", wf_body)
        wf_id = created["id"]
        print(f"Created workflow {wf_id}")
        activate_via_rest(wf_id)
        print("Activated; triggering webhook…")
        time.sleep(2)
        try:
            trigger_webhook()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            print(f"webhook error {exc.code}: {body[:500]}", file=sys.stderr)
            raise
        status = wait_execution(wf_id)
        print(f"Execution status: {status}")
        if status != "success":
            return 1
        return 0
    finally:
        if wf_id:
            try:
                deactivate_via_rest(wf_id)
                n8n_api_request("DELETE", f"/workflows/{wf_id}")
                print(f"Deleted temporary workflow {wf_id}")
            except Exception as exc:
                print(f"cleanup warning: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
