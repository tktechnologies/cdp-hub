# Google Sheets pipeline fix (2026-05-21)

## Symptom

No new rows in **cdp_resultados** (`1ZBU2d3XVsngOYQH12yU7Mg9DcIzVet2dDmhMtZqHSOo`) — tabs Detalhado / Historico / Resumo.

## Root causes (two)

### 1. Webhook secret mismatch (blocked entire pipeline)

- Worker (A27) sends trimmed `X-Webhook-Secret` (no `\r\n`).
- n8n `CDP_CALLBACK_WEBHOOK_SECRET` had trailing `\r\r\n` from Key Vault / container secret.
- IF node **🔐 Verificar Webhook Secret** failed → executions ended in ~1–2s (no Wait, no Sheets).

**Fix applied:** Updated `cdp-n8n-prod` container secret `callback-webhook-secret` with trimmed value; new revision `cdp-n8n-prod--0000012`.

### 2. Stale Google Sheets tab IDs (gid cache)

- Sheet nodes used `mode: list` + numeric gid from an old spreadsheet (`1O6H__...` / `1TFSb8...`).
- Live spreadsheet `1ZBU2d3...` → error `Sheet with ID 1831011286 not found`.

**Fix applied:** Repo + live publish — `sheetName.mode: name` with tab names `Detalhado`, `Historico`, `Resumo`, `SKUs`.

## Verification

| Execution | Job | Secret IF | Detalhado/Historico/Resumo | Failure |
|-----------|-----|-----------|----------------------------|---------|
| 380 | a28-verify | FAIL | skipped | secret |
| 403 | 85c64844-... | PASS | FAIL at Detalhado | stale gid |
| 405 | dbe7291d-... | PASS | PASS (ran ~42s) | CDP_SKUs NOTIFICADO stale gid |

After second publish (SKUs by name), re-check execution for job `dbe7291d-3e20-403d-a52a-59a4fd9dab49` or run a new 1-SKU test.

## Live n8n

- Workflow: `cdp_resultado` `VfBSV3WU6on8BXm8`
- Active version (sheets+secret): `0ddea5ee-99fc-4818-9cc7-8efc4af869ec` (first publish)
- Second publish: SKUs tab fix (see n8n UI for latest active version id)

## Optional follow-up

- Trim Key Vault `callback-webhook-secret` and `api-key` at source (A29) — needs `setSecret` permission.
- Publish `cdp_analise` with same sheet-name fixes (repo updated, live not yet).
