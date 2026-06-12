#!/usr/bin/env python3
"""Ensure n8n/workflows/cdp_notifier.json exists before DEV/prod n8n prep."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTIFIER_JSON = REPO_ROOT / "n8n" / "workflows" / "cdp_notifier.json"
PREPARE_NODE = "\U0001f4e5 Preparar pipeline-result"
FORMATTER_NODE = "\U0001f4e3 Formatar mensagem final"
PROD_TELEGRAM_CREDENTIAL = {"id": "UmDqGKD8k0bA10j2", "name": "cdp-bot-assistente"}
DEV_TELEGRAM_CREDENTIAL = {"id": "wblrlkXu6SW1M5M1", "name": "dev-cdp-bot"}
PROD_GMAIL_CREDENTIAL = {"id": "rQesNRyarukVs0N4", "name": "gmail lucas@tktech"}

DEV_WORKFLOW_REPLACEMENTS = {
    "return /^DEV\\s*-/i.test(workflowName()) || /^dev$/i.test(env('CDP_ENV'));": (
        "return /^DEV\\s*-/i.test(workflowName());"
    ),
}

PREPARE_PIPELINE_RESULT_JS = r"""// cdp_notifier - parse receiver handoff webhook and prepare pipeline-result API call.

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

function targetEnvName(name, target) {
  const prefix = target === 'stokai' ? 'CDP_STOKAI' : 'CDP_DEV';
  return {
    CDP_SCRAPER_API_BASE: `${prefix}_SCRAPER_API_BASE`,
    MUVSTOK_SCRAPER_API_BASE: `${prefix}_SCRAPER_API_BASE`,
    CDP_API_KEY: `${prefix}_API_KEY`,
    MUVSTOK_API_KEY: `${prefix}_API_KEY`,
    API_KEY: `${prefix}_API_KEY`,
  }[name] || '';
}

function envFor(name) {
  const target = workflowTarget();
  if (target === 'prod') return env(name);
  const mapped = targetEnvName(name, target);
  return mapped ? env(mapped) : env(name);
}

function trimTrailingSlashes(value) {
  let out = String(value || '').trim();
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

const wh = $('🔔 Webhook cdp-notifier').first().json;
const body = parseBody(wh.body);
const batchGroupId = String(body.batch_group_id || '').trim();
const source = String(body.source || '').trim().toLowerCase();
const status = String(body.status || 'completed').trim().toLowerCase();
const summary = body.summary && typeof body.summary === 'object' ? body.summary : {};

if (!batchGroupId || (source !== 'scraper' && source !== 'stokapi')) {
  return [{ json: { skip: true, reason: 'invalid_handoff' } }];
}

const apiBase = trimTrailingSlashes(
  envFor('CDP_SCRAPER_API_BASE') || envFor('MUVSTOK_SCRAPER_API_BASE') || ''
);
const apiKey = envFor('CDP_API_KEY') || envFor('MUVSTOK_API_KEY') || envFor('API_KEY');

return [
  {
    json: {
      skip: false,
      pipeline_result_url:
        apiBase + '/api/v1/dispatch-runs/by-batch/' + encodeURIComponent(batchGroupId) + '/pipeline-result',
      pipeline_result_api_key: apiKey,
      pipeline_result_body: {
        source,
        status,
        summary,
      },
      handoff: body,
    },
  },
];
"""

FINAL_FORMATTER_JS = r"""// cdp_notifier - format one final Telegram/email from the aggregate pipeline claim.

const WEBSCRAPERS_LABEL = 'WEBSCRAPERS';
const ESTOQUE_LABEL = 'ESTOQUE ONLINE';

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

function isDevWorkflow() {
  return /^DEV\s*-/i.test(workflowName());
}

function envFor(name) {
  if (!isDevWorkflow()) return env(name);
  const map = { CDP_RESULTADOS_SHEETS_URL: 'CDP_DEV_RESULTADOS_SHEETS_URL' };
  const mapped = map[name] || '';
  return mapped ? env(mapped) : env(name);
}

function reportUrl() {
  const configured = envFor('CDP_RESULTADOS_SHEETS_URL');
  if (configured || isDevWorkflow()) return configured;
  return 'https://docs.google.com/spreadsheets/d/1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo/edit#gid=2127243308';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function durPt(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  if (s >= 3600) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return h + 'h' + (m ? ' ' + m + 'min' : '');
  }
  if (s >= 60) return Math.floor(s / 60) + ' min';
  return s > 0 ? s + ' s' : '';
}

function pecaLabel(n) {
  const x = Number(n) || 0;
  return x === 1 ? '1 pe\u00e7a' : x + ' pe\u00e7as';
}

function consultaLine(n) {
  const x = Number(n) || 0;
  if (!x) return 'Resultado consolidado de sites e estoque.';
  return pecaLabel(x) + (x === 1 ? ' consultada em sites e estoque.' : ' consultadas em sites e estoque.');
}

function numberField(summary, key) {
  return Number((summary || {})[key]) || 0;
}

function totalSignals(summary) {
  return (
    numberField(summary, 'with_price') +
    numberField(summary, 'no_price') +
    numberField(summary, 'not_found') +
    numberField(summary, 'blocked') +
    numberField(summary, 'errors')
  );
}

function sectionLines(icon, label, summary) {
  const s = summary || {};
  const lines = [icon + ' *' + label + '*'];
  lines.push('Com pre\u00e7o: *' + numberField(s, 'with_price') + '*');
  if (numberField(s, 'no_price') > 0) lines.push('Sem pre\u00e7o: *' + numberField(s, 'no_price') + '*');
  if (numberField(s, 'not_found') > 0) lines.push('N\u00e3o encontrado: *' + numberField(s, 'not_found') + '*');
  if (numberField(s, 'blocked') > 0) lines.push('Bloqueado: *' + numberField(s, 'blocked') + '*');
  if (numberField(s, 'errors') > 0) lines.push('Erros/timeouts: *' + numberField(s, 'errors') + '*');
  const dur = durPt(s.duration_seconds);
  if (dur) lines.push('Dura\u00e7\u00e3o: ' + dur);
  if (totalSignals(s) === 0) lines.push('Sem resumo registrado.');
  if (String(s.status || '').toLowerCase() === 'failed') {
    lines.push('Status: falha' + (s.failed_reason ? ' - ' + String(s.failed_reason).slice(0, 120) : ''));
  }
  return lines;
}

function sectionHtml(label, summary) {
  const s = summary || {};
  const warning =
    numberField(s, 'blocked') > 0 || numberField(s, 'errors') > 0 || String(s.status || '').toLowerCase() === 'failed';
  return (
    '<div style="border:1px solid #e5e7eb;border-radius:8px;padding:14px 16px;margin:0 0 12px">' +
    '<div style="font-size:13px;color:#111827;font-weight:700;margin-bottom:8px">' +
    escapeHtml(label) +
    '</div>' +
    '<div style="font-size:14px;line-height:1.7;color:#374151">' +
    '<strong>Com pre\u00e7o:</strong> ' +
    numberField(s, 'with_price') +
    '<br><strong>Sem pre\u00e7o:</strong> ' +
    numberField(s, 'no_price') +
    '<br><strong>N\u00e3o encontrado:</strong> ' +
    numberField(s, 'not_found') +
    '<br><strong>Bloqueado:</strong> ' +
    numberField(s, 'blocked') +
    '<br><strong>Erros/timeouts:</strong> ' +
    numberField(s, 'errors') +
    (s.duration_seconds ? '<br><strong>Dura\u00e7\u00e3o:</strong> ' + escapeHtml(durPt(s.duration_seconds)) : '') +
    (warning ? '<br><strong>Status:</strong> conclu\u00eddo com avisos' : '') +
    '</div>' +
    '</div>'
  );
}

const apiResp = $input.first().json;
const claim = apiResp.claim || apiResp.body?.claim || null;
if (!apiResp.ready_for_final || !claim) {
  return [{ json: { skip_send: true, not_ready: true, reason: 'not_ready' } }];
}

const scraper = claim.scraper_summary || {};
const stokapi = claim.stokapi_summary || {};
const url = reportUrl();
const totalSkus = Number(claim.total_skus) || 0;
const consultadaLine = consultaLine(totalSkus);
const totalWithPrice = numberField(scraper, 'with_price') + numberField(stokapi, 'with_price');
const hasWarnings =
  numberField(scraper, 'blocked') +
    numberField(scraper, 'errors') +
    numberField(stokapi, 'blocked') +
    numberField(stokapi, 'errors') >
  0;

let replyChannel = String(claim.reply_channel || '').trim().toLowerCase();
const chatId = String(claim.chat_id || '').trim();
const replyEmail = String(claim.reply_email || '').trim();

if (!replyChannel) {
  if (replyEmail) replyChannel = 'email';
  else if (chatId) replyChannel = 'telegram';
}

if (!chatId && !replyEmail) {
  return [
    {
      json: {
        skip_send: true,
        skipped_no_target: true,
        run_id: claim.run_id,
        sheet_row_numbers: claim.sheet_row_numbers || [],
      },
    },
  ];
}

const tgLines = [
  '\u{1F916} *Assistente CDP*',
  '',
  '\u2705 *Consulta CDP conclu\u00edda*',
  consultadaLine,
  'Resultados com pre\u00e7o: *' + totalWithPrice + '*',
  '',
];
tgLines.push(...sectionLines('\u{1F50E}', WEBSCRAPERS_LABEL, scraper));
tgLines.push('');
tgLines.push(...sectionLines('\u{1F4E6}', ESTOQUE_LABEL, stokapi));
if (url) {
  tgLines.push('');
  tgLines.push('\u{1F4CE} Relat\u00f3rio: ' + url);
}

const htmlSections =
  '<h2 style="margin:0 0 8px;font-size:20px;color:#111827">Consulta CDP conclu\u00edda</h2>' +
  '<p style="margin:0 0 16px;font-size:14px;line-height:1.6;color:#475569">' +
  escapeHtml(consultadaLine) +
  '</p>' +
  sectionHtml(WEBSCRAPERS_LABEL, scraper) +
  sectionHtml(ESTOQUE_LABEL, stokapi) +
  (url
    ? '<p style="margin:18px 0 0"><a href="' +
      escapeHtml(url) +
      '" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;padding:12px 18px;font-weight:700">Abrir relat\u00f3rio</a></p>'
    : '');

const scraperJobIds = Array.isArray(claim.scraper_job_ids) ? claim.scraper_job_ids : [];
const scraperJobId = String(scraperJobIds[0] || '').trim();

return [
  {
    json: {
      skip_send: false,
      run_id: claim.run_id,
      batch_group_id: String(claim.batch_group_id || '').trim(),
      scraper_job_id: scraperJobId,
      scraper_job_ids: scraperJobIds,
      stokapi_job_id: String(claim.stokapi_job_id || '').trim(),
      reply_channel: replyChannel,
      chat_id: chatId,
      email_to: replyEmail,
      sheet_row_numbers: claim.sheet_row_numbers || [],
      msg_telegram: tgLines.join('\n'),
      msg_email_subject: 'Consulta CDP conclu\u00edda - resultado consolidado',
      msg_email_html:
        '<div style="font-family:Arial,sans-serif;color:#1f2937;max-width:640px">' + htmlSections + '</div>',
    },
  },
];
"""


def main() -> int:
    if NOTIFIER_JSON.is_file():
        workflow = json.loads(NOTIFIER_JSON.read_text(encoding="utf-8"))
        changed = False
        for node in workflow.get("nodes", []):
            params = node.setdefault("parameters", {})
            code = params.get("jsCode")
            if isinstance(code, str):
                for old, new in DEV_WORKFLOW_REPLACEMENTS.items():
                    if old in code:
                        code = code.replace(old, new)
                        changed = True
                params["jsCode"] = code
            if node.get("name") == PREPARE_NODE:
                params["jsCode"] = PREPARE_PIPELINE_RESULT_JS
                changed = True
            if node.get("name") == FORMATTER_NODE:
                params["jsCode"] = FINAL_FORMATTER_JS
                changed = True
            if node.get("type") == "n8n-nodes-base.telegram":
                creds = node.setdefault("credentials", {})
                target = (
                    DEV_TELEGRAM_CREDENTIAL
                    if "DEV -" in workflow.get("name", "")
                    else PROD_TELEGRAM_CREDENTIAL
                )
                if creds.get("telegramApi") != target:
                    creds["telegramApi"] = dict(target)
                    changed = True
                af = params.setdefault("additionalFields", {})
                if af.get("appendAttribution") is not False:
                    af["appendAttribution"] = False
                    changed = True
            if (
                node.get("type") == "n8n-nodes-base.gmail"
                and node.get("name") == "📧 Email: resultado final"
                and "DEV -" not in workflow.get("name", "")
            ):
                creds = node.setdefault("credentials", {})
                if creds.get("gmailOAuth2") != PROD_GMAIL_CREDENTIAL:
                    creds["gmailOAuth2"] = dict(PROD_GMAIL_CREDENTIAL)
                    changed = True
        if changed:
            NOTIFIER_JSON.write_text(
                json.dumps(workflow, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if any(node.get("name") == FORMATTER_NODE for node in workflow.get("nodes", [])):
            print(f"OK: patched {NOTIFIER_JSON.relative_to(REPO_ROOT)}")
            return 0
        print(
            f"Missing formatter node {FORMATTER_NODE!r} in {NOTIFIER_JSON.relative_to(REPO_ROOT)}.",
            file=sys.stderr,
        )
        return 1
    print(
        f"Missing {NOTIFIER_JSON.relative_to(REPO_ROOT)}.\n"
        "Fetch the live cdp_notifier workflow from n8n "
        "(workflow ID ennI9nKin9ruPaLO on automacao.tktechnologies.com.br) "
        "and save it to that path before running make n8n-dev-workflows.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
