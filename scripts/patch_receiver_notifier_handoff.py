#!/usr/bin/env python3
"""Ensure aggregate notifier handoff nodes exist on scraper/stokapi receivers."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRAPER_JSON = REPO_ROOT / "n8n" / "workflows" / "cdp_scraper.json"
STOKAPI_JSON = REPO_ROOT / "n8n" / "workflows" / "cdp_stokapi.json"
HANDOFF_NODE = "📣 Preparar handoff notifier"
POST_NODE = "📤 POST cdp-notifier"

SCRAPER_HANDOFF_JS = r"""// cdp_scraper — POST aggregate pipeline handoff to cdp_notifier after Sheets writes.

function parseBody(raw) {
  let p = raw;
  if (typeof p === 'string') {
    try {
      p = JSON.parse(p);
    } catch (e) {
      p = {};
    }
  }
  return p && typeof p === 'object' ? p : {};
}

function env(name) {
  try {
    if (typeof $env !== 'undefined' && $env && $env[name]) {
      return String($env[name]).trim();
    }
  } catch (e) {}
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
  return '';
}

function workflowName() {
  try {
    if (typeof $workflow !== 'undefined' && $workflow && $workflow.name) {
      return String($workflow.name).trim();
    }
  } catch (e) {}
  return '';
}

function workflowTarget() {
  const name = workflowName();
  if (/^DEV\s*-/i.test(name)) return 'dev';
  if (/^STOKAI\s*-/i.test(name)) return 'stokai';
  return 'prod';
}

function isDevWorkflow() {
  return workflowTarget() === 'dev';
}

function envFor(name) {
  const target = workflowTarget();
  if (target === 'prod') return env(name);
  const prefix = target === 'stokai' ? 'CDP_STOKAI' : 'CDP_DEV';
  const map = {
    CDP_NOTIFIER_WEBHOOK_URL: `${prefix}_NOTIFIER_WEBHOOK_URL`,
    WEBHOOK_URL: `${prefix}_WEBHOOK_URL`,
    CDP_NOTIFIER_WEBHOOK_PATH: `${prefix}_NOTIFIER_WEBHOOK_PATH`,
  };
  const mapped = map[name] || '';
  if (!mapped) return env(name);
  const value = env(mapped);
  if (value) return value;
  if (name === 'CDP_NOTIFIER_WEBHOOK_PATH') {
    return target === 'stokai' ? 'webhook/stokai-cdp-notifier' : 'webhook/dev-cdp-notifier';
  }
  return '';
}

function defaultNotifierWebhookPath() {
  const target = workflowTarget();
  if (target === 'stokai') return 'webhook/stokai-cdp-notifier';
  if (target === 'dev') return 'webhook/dev-cdp-notifier';
  return 'webhook/cdp-notifier';
}

function trimTrailingSlashes(value) {
  let out = String(value || '').trim();
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}

function trimSlashes(value) {
  let out = String(value || '').trim();
  while (out.startsWith('/')) out = out.slice(1);
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}

function numericPrice(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function partHasValidPrice(part) {
  return !!(part && part.exact_match && numericPrice(part.price) !== null);
}

function siteParts(site) {
  if (Array.isArray(site?.results)) return site.results;
  if (Array.isArray(site?.parts)) return site.parts;
  return [];
}

function siteHasValidPrice(site) {
  if (site?.has_valid_price === true || String(site?.sku_result || '').toUpperCase() === 'FOUND_PRICE') {
    return true;
  }
  return siteParts(site).some(partHasValidPrice);
}

function siteHasExactEvidence(site) {
  if (String(site?.sku_result || '').toUpperCase() === 'NO_PRICE') return true;
  if (String(site?.status || '').toLowerCase() === 'no_price') return true;
  return siteParts(site).some((part) => !!part?.exact_match);
}

function skuHasValidPrice(row) {
  if (row?.has_valid_price === true || String(row?.sku_result || '').toUpperCase() === 'FOUND_PRICE') {
    return true;
  }
  const best = row?.best_price || null;
  if (best && best.exact_match !== false && numericPrice(best.price) !== null) return true;
  return (Array.isArray(row?.site_results) ? row.site_results : []).some(siteHasValidPrice);
}

function canonicalSkuStatus(row) {
  const explicit = String(row?.sku_result || '').trim().toUpperCase();
  if (explicit) return explicit;
  const sites = Array.isArray(row?.site_results) ? row.site_results : [];
  if (skuHasValidPrice(row)) return 'FOUND_PRICE';
  if (row?.has_any_exact_evidence === true || sites.some(siteHasExactEvidence)) return 'NO_PRICE';
  const statuses = sites.map((site) => String(site?.sku_result || site?.status || '').trim().toUpperCase());
  if (statuses.includes('BLOCKED')) return 'BLOCKED';
  if (statuses.includes('TIMEOUT')) return 'TIMEOUT';
  if (statuses.includes('ERROR')) return 'ERROR';
  return 'NOT_FOUND';
}

function countScraperSummary(results) {
  const totals = { with_price: 0, no_price: 0, not_found: 0, blocked: 0, errors: 0 };
  for (const row of results || []) {
    const status = canonicalSkuStatus(row);
    if (status === 'FOUND_PRICE') totals.with_price += 1;
    else if (status === 'NO_PRICE') totals.no_price += 1;
    else if (status === 'BLOCKED') totals.blocked += 1;
    else if (status === 'TIMEOUT' || status === 'ERROR') totals.errors += 1;
    else totals.not_found += 1;
  }
  return totals;
}

const wh = $('🔔 Webhook: Receber Resultados').first().json;
const payload = parseBody(wh.body);
const q = wh.query || {};
const jmeta =
  typeof payload.job_metadata === 'object' && payload.job_metadata !== null
    ? payload.job_metadata
    : typeof payload.metadata === 'object' && payload.metadata !== null
      ? payload.metadata
      : {};

const deliveryMode = String(jmeta.delivery_mode || q.delivery_mode || '').trim().toLowerCase();
if (deliveryMode !== 'aggregate') {
  return [];
}

const batchGroupId = String(jmeta.batch_group_id || q.batch_group_id || '').trim();
if (!batchGroupId) {
  return [];
}

const totals = countScraperSummary(payload.results || []);
const jobStatus = String(payload.status || '').toLowerCase();
const pipelineStatus = jobStatus === 'failed' ? 'failed' : 'completed';

let notifierUrl = envFor('CDP_NOTIFIER_WEBHOOK_URL');
if (!notifierUrl) {
  const base = trimTrailingSlashes(envFor('WEBHOOK_URL') || 'https://automacao.tktechnologies.com.br');
  const rel = trimSlashes(envFor('CDP_NOTIFIER_WEBHOOK_PATH') || defaultNotifierWebhookPath());
  notifierUrl = base + '/' + rel;
}

return [
  {
    json: {
      notifier_url: notifierUrl,
      handoff_body: {
        batch_group_id: batchGroupId,
        source: 'scraper',
        status: pipelineStatus,
        summary: {
          ...totals,
          duration_seconds: Number(payload.duration_seconds) || null,
          status: pipelineStatus,
          failed_reason: pipelineStatus === 'failed' ? String(payload.error || '') : null,
        },
      },
    },
  },
];
"""

STOKAPI_HANDOFF_JS = r"""// cdp_stokapi — POST aggregate pipeline handoff to cdp_notifier after Sheets writes.

function env(name) {
  try {
    if (typeof $env !== 'undefined' && $env && $env[name]) {
      return String($env[name]).trim();
    }
  } catch (e) {}
  try {
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
      return String(process.env[name]).trim();
    }
  } catch (e) {}
  return '';
}

function workflowName() {
  try {
    if (typeof $workflow !== 'undefined' && $workflow && $workflow.name) {
      return String($workflow.name).trim();
    }
  } catch (e) {}
  return '';
}

function workflowTarget() {
  const name = workflowName();
  if (/^DEV\s*-/i.test(name)) return 'dev';
  if (/^STOKAI\s*-/i.test(name)) return 'stokai';
  return 'prod';
}

function isDevWorkflow() {
  return workflowTarget() === 'dev';
}

function envFor(name) {
  const target = workflowTarget();
  if (target === 'prod') return env(name);
  const prefix = target === 'stokai' ? 'CDP_STOKAI' : 'CDP_DEV';
  const map = {
    CDP_NOTIFIER_WEBHOOK_URL: `${prefix}_NOTIFIER_WEBHOOK_URL`,
    WEBHOOK_URL: `${prefix}_WEBHOOK_URL`,
    CDP_NOTIFIER_WEBHOOK_PATH: `${prefix}_NOTIFIER_WEBHOOK_PATH`,
  };
  const mapped = map[name] || '';
  if (!mapped) return env(name);
  const value = env(mapped);
  if (value) return value;
  if (name === 'CDP_NOTIFIER_WEBHOOK_PATH') {
    return target === 'stokai' ? 'webhook/stokai-cdp-notifier' : 'webhook/dev-cdp-notifier';
  }
  return '';
}

function defaultNotifierWebhookPath() {
  const target = workflowTarget();
  if (target === 'stokai') return 'webhook/stokai-cdp-notifier';
  if (target === 'dev') return 'webhook/dev-cdp-notifier';
  return 'webhook/cdp-notifier';
}

function trimTrailingSlashes(value) {
  let out = String(value || '').trim();
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}

function trimSlashes(value) {
  let out = String(value || '').trim();
  while (out.startsWith('/')) out = out.slice(1);
  while (out.endsWith('/')) out = out.slice(0, -1);
  return out;
}

function parseBody(raw) {
  let p = raw;
  if (typeof p === 'string') {
    try {
      p = JSON.parse(p);
    } catch (e) {
      p = {};
    }
  }
  return p && typeof p === 'object' ? p : {};
}

function rowPrice(row) {
  const n = Number(row?.valorPrecoVenda ?? row?.valorprecovenda ?? row?.valorprecavenda ?? row?.price ?? row?.preco);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function countPayloadSummary(payload) {
  const totals = { with_price: 0, no_price: 0, not_found: 0, blocked: 0, errors: 0 };
  const results = Array.isArray(payload.results) ? payload.results : [];
  for (const item of results) {
    const rows = Array.isArray(item.rows) ? item.rows : Array.isArray(item.listings) ? item.listings : [];
    const status = String(item.sku_result || item.status || '').trim().toUpperCase();
    if (rows.some((row) => rowPrice(row) !== null)) totals.with_price += 1;
    else if (rows.length) totals.no_price += 1;
    else if (status === 'BLOCKED') totals.blocked += 1;
    else if (status === 'TIMEOUT' || status === 'ERROR' || status === 'FAILED') totals.errors += 1;
    else totals.not_found += 1;
  }
  return totals;
}

let j = {};
try {
  if (typeof $getWorkflowStaticData === 'function') {
    j = $getWorkflowStaticData('global').muvstok_last_callback || {};
  }
} catch (e) {}

const wh = $('🔔 Webhook API Diversos Result').first().json;
const payload = parseBody(wh.body);
const q = wh.query || {};
const jmeta =
  typeof payload.metadata === 'object' && payload.metadata !== null
    ? payload.metadata
    : typeof payload.job_metadata === 'object' && payload.job_metadata !== null
      ? payload.job_metadata
      : {};

const deliveryMode = String(jmeta.delivery_mode || q.delivery_mode || j.delivery_mode || '')
  .trim()
  .toLowerCase();
if (deliveryMode !== 'aggregate') {
  return [];
}

const batchGroupId = String(jmeta.batch_group_id || q.batch_group_id || j.batch_group_id || '').trim();
if (!batchGroupId) {
  return [];
}

const fail = Number(j.failed_sku_count) || Number(payload.failed_sku_count) || 0;
const ok = Number(j.succeeded_sku_count) || Number(payload.succeeded_sku_count) || 0;
const pipelineStatus = fail > 0 && ok === 0 ? 'failed' : 'completed';
const fallback = countPayloadSummary(payload);

let notifierUrl = envFor('CDP_NOTIFIER_WEBHOOK_URL');
if (!notifierUrl) {
  const base = trimTrailingSlashes(envFor('WEBHOOK_URL') || 'https://automacao.tktechnologies.com.br');
  const rel = trimSlashes(envFor('CDP_NOTIFIER_WEBHOOK_PATH') || defaultNotifierWebhookPath());
  notifierUrl = base + '/' + rel;
}

return [
  {
    json: {
      notifier_url: notifierUrl,
      handoff_body: {
        batch_group_id: batchGroupId,
        source: 'stokapi',
        status: pipelineStatus,
        summary: {
          with_price: Number(j.found_sku_count) || Number(j.priced_sku_count) || fallback.with_price,
          no_price: Number(j.no_price_sku_count) || fallback.no_price,
          not_found: Number(j.not_found_sku_count) || fallback.not_found,
          blocked: Number(j.blocked_sku_count) || fallback.blocked,
          errors: Number(j.error_sku_count) || Number(j.failed_sku_count) || fallback.errors,
          duration_seconds: Number(j.duration_seconds) || Number(payload.duration_seconds) || null,
          status: pipelineStatus,
          failed_reason: pipelineStatus === 'failed' ? String(j.error || j.error_text || '') : null,
        },
      },
    },
  },
];
"""


def _nid() -> str:
    return str(uuid.uuid4())


def _find_node(nodes: list[dict], name: str) -> dict | None:
    for node in nodes:
        if node.get("name") == name:
            return node
    return None


def _ensure_handoff_nodes(
    wf: dict,
    *,
    handoff_js: str,
    after_node: str,
    default_post_targets: list[str] | None = None,
) -> None:
    nodes = wf.setdefault("nodes", [])
    conns = wf.setdefault("connections", {})

    prep = _find_node(nodes, HANDOFF_NODE)
    if prep is None:
        prep = {
            "parameters": {"jsCode": handoff_js, "mode": "runOnceForAllItems"},
            "id": _nid(),
            "name": HANDOFF_NODE,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [3200, 400],
            "notes": "Aggregate delivery: POST compact summary to cdp_notifier.",
        }
        post = {
            "parameters": {
                "method": "POST",
                "url": "={{ $json.notifier_url }}",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json.handoff_body) }}",
                "options": {"timeout": 30000},
            },
            "id": _nid(),
            "name": POST_NODE,
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [3440, 400],
            "continueOnFail": True,
        }
        nodes.extend([prep, post])
    else:
        prep["parameters"]["jsCode"] = handoff_js

    old_targets = [
        link["node"]
        for link in conns.get(after_node, {}).get("main", [[]])[0]
        if link.get("node") != HANDOFF_NODE
    ]
    existing_post_targets = [
        link["node"]
        for link in conns.get(POST_NODE, {}).get("main", [[]])[0]
        if link.get("node") != HANDOFF_NODE
    ]
    post_targets = old_targets or existing_post_targets or (default_post_targets or [])
    conns[after_node] = {"main": [[{"node": HANDOFF_NODE, "type": "main", "index": 0}]]}
    conns[HANDOFF_NODE] = {"main": [[{"node": POST_NODE, "type": "main", "index": 0}]]}
    conns[POST_NODE] = {
        "main": [[{"node": name, "type": "main", "index": 0} for name in post_targets]]
    }


def main() -> int:
    scraper = json.loads(SCRAPER_JSON.read_text(encoding="utf-8"))
    stokapi = json.loads(STOKAPI_JSON.read_text(encoding="utf-8"))

    _ensure_handoff_nodes(
        scraper,
        handoff_js=SCRAPER_HANDOFF_JS,
        after_node="📋 Salvar → CDP_Resultados (Resumo)",
        default_post_targets=["📣 Formatar Notificação Conclusão"],
    )
    SCRAPER_JSON.write_text(json.dumps(scraper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {SCRAPER_JSON.relative_to(REPO_ROOT)}")

    resumo_name = "📋 Salvar → CDP_Resultados (Resumo)"
    if _find_node(stokapi.get("nodes", []), resumo_name) is None:
        resumo_name = next(
            (
                node["name"]
                for node in stokapi.get("nodes", [])
                if "Resumo" in node.get("name", "") and "Salvar" in node.get("name", "")
            ),
            resumo_name,
        )

    _ensure_handoff_nodes(stokapi, handoff_js=STOKAPI_HANDOFF_JS, after_node=resumo_name)
    STOKAPI_JSON.write_text(json.dumps(stokapi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Patched {STOKAPI_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
