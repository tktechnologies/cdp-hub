#!/usr/bin/env python3
"""Inject n8n/src JS into cdp_router workflow Code nodes."""
from __future__ import annotations

import json
import pathlib
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED = ROOT / "n8n" / "src"
sys.path.insert(0, str(ROOT / "scripts"))
from cdp_skus_sheet_columns import sheet_column_id, sheet_display_name  # noqa: E402

NODE_FILES = {
    "🔍 DQ: Validar & Deduplicar": "router_dq.js",
    "🎲 Limitar SKUs": "router_limitar_skus.js",
    "🎲 Limitar SKUs (teste — remover depois)": "router_limitar_skus.js",
    "⚙️ Formatar Payload (Batches)": "formatar_payload_scraper.js",
    "⚙️ Formatar Payload Scraper": "formatar_payload_scraper.js",
    "📤 Router: Muvstok": "router_stokapi.js",
    "📤 Router: StokAPI": "router_stokapi.js",
    "📤 Router: API Diversos": "router_stokapi.js",
    "❌ Formatar Erro de Despacho": "router_error_scraper.js",
    "📋 Formatar erro Muvstok": "router_error_stokapi.js",
    "📋 Formatar erro StokAPI": "router_error_stokapi.js",
    "📋 Formatar erro API Diversos": "router_error_stokapi.js",
    "🔗 Emparelhar SKUs → PROCESSADO": "emparelhar_scraper.js",
    "📋 Formatar Confirmação (Planilha)": "router_confirmacao.js",
    "📱 Roteador de Comando": "router_telegram.js",
    "📊 Registrar Execução": "router_register_run.js",
    "📊 Status: preparar": "router_status_prepare.js",
    "📊 Formatar Status": "router_status.js",
    "📊 Progress: preparar runs": "progress_poll.js",
    "📊 Progress: formatar": "progress_format.js",
    "💾 Salvar Contexto do Solicitante": "router_save_context.js",
}

RENAME_NODES = {
    "🎲 Limitar SKUs (teste — remover depois)": "🎲 Limitar SKUs",
    "⚙️ Formatar Payload (Batches)": "⚙️ Formatar Payload Scraper",
    "📤 Router: Muvstok": "📤 Router: StokAPI",
    "🚀 POST Muvstok API": "🚀 POST StokAPI",
    "📦 Muvstok job aceito?": "📦 StokAPI job aceito?",
    "📋 Formatar erro Muvstok": "📋 Formatar erro StokAPI",
    "📱 Telegram: erro Muvstok": "📱 Telegram: erro StokAPI",
    "❓ Disparar Muvstok?": "❓ Disparar StokAPI?",
}

LEGACY_SAMPLE_MARKERS = (
    "const FIXED_DISPATCH_MAX_SKUS = 5",
    "const FIXED_MAX_SKUS = 5",
)

PARAMETER_PATCHES = {
    "🚀 POST → Scraper API (/jobs)": {
        "url": "={{ $json.api_jobs_url }}",
        "header:X-API-Key": "={{ $json.api_key }}",
        "jsonBody": (
            "={{ JSON.stringify({ items: $json.items, sites: $json.sites, "
            "callback_url: $json.callback_url, priority: $json.priority || 5, "
            "force_refresh: $json.force_refresh === true, "
            "batch_group_id: $json.batch_group_id, "
            "chat_id: $json.reply_channel === 'telegram' ? $json.chat_id : undefined, "
            "command_route: $json.command_route, metadata: $json.metadata, "
            "reply_channel: $json.reply_channel, command_origin: $json.command_origin, "
            "reply_email: $json.reply_email, notify: $json.notify }) }}"
        ),
    },
    "🚀 POST API Diversos": {
        "header:X-API-Key": "={{ $json.api_key }}",
    },
    "📊 GET dispatch run (chat)": {
        "url": "={{ $json.dispatch_runs_lookup_url }}",
        "header:X-API-Key": "={{ $json.dispatch_runs_api_key }}",
    },
    "📥 Obter Path do Arquivo (Telegram)": {
        "url": "={{ 'https://api.telegram.org/bot' + $json.telegram_bot_token + '/getFile' }}",
    },
    "📥 Baixar Arquivo (Telegram)": {
        "url": "={{ 'https://api.telegram.org/file/bot' + $('📱 Roteador de Comando').first().json.telegram_bot_token + '/' + $json.result.file_path }}",
    },
    "📧 Enviar Alerta de Erro": {
        "sendTo": "={{ $json.email_from || '' }}",
    },
    "📧 Confirmar Planilha (Email)": {
        "options": {"appendAttribution": False},
    },
}


PROGRESS_WORKFLOW = ROOT / "n8n" / "workflows" / "cdp_progress.json"


def schema_entry(col_id: str, col_type: str, *, read_only: bool = False) -> dict:
    actual_col_id = sheet_column_id(col_id)
    entry = {
        "id": actual_col_id,
        "displayName": sheet_display_name(col_id),
        "required": False,
        "defaultMatch": False,
        "display": True,
        "type": col_type,
        "canBeUsedToMatch": True,
    }
    if read_only:
        entry["readOnly"] = True
        entry["removed"] = False
    return entry


def patch_router_processado_node(node: dict) -> None:
    if node.get("name") != "✅ Marcar PROCESSADO → CDP_SKUs":
        return
    columns = node.setdefault("parameters", {}).setdefault("columns", {})
    columns["mappingMode"] = "defineBelow"
    columns["value"] = {
        "row_number": "={{ $json.row_number }}",
        sheet_column_id("PROCESSADO"): "={{ $json.PROCESSADO }}",
        sheet_column_id("ENCONTRADO"): "={{ $json.ENCONTRADO }}",
        sheet_column_id("NOTIFICADO"): "={{ $json.NOTIFICADO }}",
    }
    columns["matchingColumns"] = ["row_number"]
    columns["schema"] = [
        schema_entry("row_number", "number", read_only=True),
        schema_entry("PROCESSADO", "string"),
        schema_entry("ENCONTRADO", "string"),
        schema_entry("NOTIFICADO", "string"),
    ]
    columns["attemptToConvertTypes"] = False
    columns["convertFieldsToString"] = True
    node["notes"] = (
        "Updates PROCESSADO/ENCONTRADO/NOTIFICADO=⏳ Processando for each dispatched "
        "sheet row, matched by row_number so duplicate CODIGO rows are initialized too."
    )


def patch_router_sheet_read_node(node: dict) -> None:
    if node.get("name") != "📊 Ler CDP_SKUs":
        return
    node["alwaysOutputData"] = True
    node["notes"] = (
        "Always emits one item when the sheet read is empty, so DQ can send a "
        "clear no-pending-SKUs reply instead of ending the command silently."
    )


def new_id() -> str:
    return str(uuid.uuid4())


def find_node(nodes: list[dict], name: str) -> dict | None:
    return next((node for node in nodes if node.get("name") == name), None)


def ensure_code_node(nodes: list[dict], name: str, position: list[int], notes: str) -> None:
    node = find_node(nodes, name)
    if node is None:
        nodes.append(
            {
                "parameters": {"jsCode": "", "mode": "runOnceForAllItems"},
                "id": new_id(),
                "name": name,
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": position,
                "notes": notes,
            }
        )
        return
    node["type"] = "n8n-nodes-base.code"
    node["typeVersion"] = node.get("typeVersion", 2)
    node.setdefault("parameters", {})["mode"] = "runOnceForAllItems"
    node["position"] = node.get("position") or position
    node["notes"] = notes


def ensure_post_dispatch_runs_node(nodes: list[dict]) -> None:
    name = "📋 POST dispatch-runs"
    node = find_node(nodes, name)
    if node is None:
        node = {
            "parameters": {},
            "id": new_id(),
            "name": name,
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [2448, 2528],
            "continueOnFail": True,
        }
        nodes.append(node)
    node["parameters"] = {
        "method": "POST",
        "url": "={{ $json.dispatch_runs_url }}",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "Content-Type", "value": "application/json"},
                {"name": "X-API-Key", "value": "={{ $json.dispatch_runs_api_key }}"},
            ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": (
            "={{ JSON.stringify({ batch_group_id: $json.batch_group_id, "
            "chat_id: $json.chat_id, command_route: $json.command_route, "
            "scraper_job_ids: $json.scraper_job_ids, stokapi_job_id: $json.stokapi_job_id, "
            "total_skus: $json.total_skus, estimated_seconds: $json.estimated_seconds, "
            "dispatched_at: $json.dispatched_at, reply_channel: $json.reply_channel, "
            "reply_email: $json.reply_email, command_origin: $json.command_origin, "
            "progress_enabled: $json.progress_enabled, delivery_mode: $json.delivery_mode, "
            "sheet_row_numbers: $json.sheet_row_numbers }) }}"
        ),
        "options": {"timeout": 15000},
    }
    node["continueOnFail"] = True


def link(node: str, index: int = 0) -> dict:
    return {"node": node, "type": "main", "index": index}


STOKAPI_ERROR_CHANNEL_IF = "❓ Erro API Diversos: Telegram?"
STOKAPI_ERROR_EMAIL_NODE = "📧 Email: erro API Diversos"
STOKAPI_ERROR_FORMAT_NODE = "📋 Formatar erro API Diversos"
STOKAPI_ERROR_TELEGRAM_NODE = "📱 Telegram: erro API Diversos"
ROUTER_GMAIL_CREDENTIAL = {"id": "rQesNRyarukVs0N4", "name": "gmail lucas@tktech"}


def ensure_stokapi_error_delivery(nodes: list[dict], conns: dict) -> None:
    """Route API Diversos dispatch errors to Telegram or email requester."""
    channel_if = next((n for n in nodes if n.get("name") == STOKAPI_ERROR_CHANNEL_IF), None)
    if channel_if is None:
        channel_if = {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "typeValidation": "strict",
                        "version": 1,
                    },
                    "conditions": [
                        {
                            "id": "tg",
                            "leftValue": "={{ $json.reply_channel }}",
                            "rightValue": "telegram",
                            "operator": {"type": "string", "operation": "equals"},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": str(uuid.uuid4()),
            "name": STOKAPI_ERROR_CHANNEL_IF,
            "type": "n8n-nodes-base.if",
            "typeVersion": 2,
            "position": [2496, 2800],
        }
        nodes.append(channel_if)

    email_node = next((n for n in nodes if n.get("name") == STOKAPI_ERROR_EMAIL_NODE), None)
    if email_node is None:
        email_node = {
            "parameters": {
                "sendTo": "={{ $json.email_to }}",
                "subject": "={{ $json.msg_email_subject }}",
                "message": "={{ $json.msg_email_html }}",
                "options": {"appendAttribution": False},
            },
            "id": str(uuid.uuid4()),
            "name": STOKAPI_ERROR_EMAIL_NODE,
            "type": "n8n-nodes-base.gmail",
            "typeVersion": 2.1,
            "position": [2720, 2880],
            "credentials": {"gmailOAuth2": dict(ROUTER_GMAIL_CREDENTIAL)},
            "continueOnFail": True,
        }
        nodes.append(email_node)

    conns[STOKAPI_ERROR_FORMAT_NODE] = {"main": [[link(STOKAPI_ERROR_CHANNEL_IF)]]}
    conns[STOKAPI_ERROR_CHANNEL_IF] = {
        "main": [
            [link(STOKAPI_ERROR_TELEGRAM_NODE)],
            [link(STOKAPI_ERROR_EMAIL_NODE)],
        ]
    }


def patch_router_http_dispatch(wf: dict, workflow_name: str) -> None:
    if workflow_name != "cdp_router":
        return

    nodes = wf.setdefault("nodes", [])
    conns = wf.setdefault("connections", {})

    wf["nodes"] = [node for node in nodes if node.get("name") != "🚀 Dispatch paralelo"]
    nodes = wf["nodes"]
    ensure_post_dispatch_runs_node(nodes)

    conns["🎲 Limitar SKUs"] = {
        "main": [
            [
                link("📤 Router: API Diversos"),
                link("⚙️ Formatar Payload Scraper"),
                link("📋 Formatar Confirmação (Planilha)"),
            ]
        ]
    }
    conns.pop("🚀 Dispatch paralelo", None)
    conns["✅ API OK?"] = {
        "main": [[link("🔗 Emparelhar SKUs → PROCESSADO"), link("📊 Registrar Execução")], [link("❌ Formatar Erro de Despacho")]]
    }
    conns["📦 API Diversos job aceito?"] = {
        "main": [[link("📊 Registrar Execução")], [link("📋 Formatar erro API Diversos")]]
    }
    conns["📊 Registrar Execução"] = {
        "main": [[link("📋 POST dispatch-runs")]]
    }
    ensure_stokapi_error_delivery(nodes, conns)

    for node in nodes:
        if node.get("name") in {
            "🚀 POST → Scraper API (/jobs)",
            "🚀 POST API Diversos",
            "📧 Enviar Alerta de Erro",
        }:
            node["continueOnFail"] = True


def set_header_value(parameters: dict, header_name: str, value: str) -> None:
    headers = parameters.setdefault("headerParameters", {}).setdefault("parameters", [])
    for header in headers:
        if header.get("name") == header_name:
            header["value"] = value
            return
    headers.append({"name": header_name, "value": value})


def apply_parameter_patches(node: dict) -> None:
    patch = PARAMETER_PATCHES.get(node.get("name", ""))
    if not patch:
        return
    parameters = node.setdefault("parameters", {})
    for key, value in patch.items():
        if key.startswith("header:"):
            set_header_value(parameters, key.split(":", 1)[1], value)
        else:
            parameters[key] = value


def patch_workflow(path: pathlib.Path) -> None:
    wf = json.loads(path.read_text(encoding="utf-8"))
    workflow_name = path.stem
    name_map = dict(RENAME_NODES)

    for node in wf.get("nodes", []):
        old_name = node.get("name", "")
        if old_name in name_map:
            node["name"] = name_map[old_name]

    patch_router_http_dispatch(wf, workflow_name)

    for node in wf.get("nodes", []):
        name = node.get("name", "")
        src = NODE_FILES.get(name)
        if not src:
            apply_parameter_patches(node)
            patch_router_processado_node(node)
            patch_router_sheet_read_node(node)
            continue
        code = (SHARED / src).read_text(encoding="utf-8")
        if node.get("type", "").endswith("code"):
            node.setdefault("parameters", {})["jsCode"] = code
            node["parameters"]["mode"] = node["parameters"].get("mode", "runOnceForAllItems")
            if name == "⚙️ Formatar Payload Scraper":
                node["notes"] = (
                    "CDP v1.0: active default sites gm,ml,vw,eu; production "
                    "CDP_SCRAPER_SITES adds melibox. Blocked sites stay disabled "
                    "until fresh proxy smoke passes."
                )
        apply_parameter_patches(node)
        patch_router_processado_node(node)
        patch_router_sheet_read_node(node)

    stale: list[str] = []
    for node in wf.get("nodes", []):
        if not node.get("type", "").endswith("code"):
            continue
        code = node.get("parameters", {}).get("jsCode", "")
        if any(m in code for m in LEGACY_SAMPLE_MARKERS):
            stale.append(node.get("name", "?"))

    conns = wf.get("connections", {})
    new_conns = {}
    for key, val in conns.items():
        new_key = name_map.get(key, key)
        new_conns[new_key] = val
    for val in new_conns.values():
        for branch in val.get("main", []):
            for link in branch:
                if link.get("node") in name_map:
                    link["node"] = name_map[link["node"]]
    wf["connections"] = new_conns
    wf["name"] = workflow_name
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {path} ({len(wf.get('nodes', []))} nodes)")
    if stale:
        print("ERROR: legacy 5-SKU cap still in nodes:", ", ".join(stale), file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    router = ROOT / "n8n" / "workflows" / "cdp_router.json"
    if not router.exists():
        print("cdp_router.json not found", file=sys.stderr)
        return 1
    patch_workflow(router)
    if PROGRESS_WORKFLOW.exists():
        patch_workflow(PROGRESS_WORKFLOW)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
