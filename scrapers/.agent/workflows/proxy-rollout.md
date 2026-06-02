# Proxy rollout workflow (Brazilian ISP / static residential)

**When:** After purchasing a validated BR ISP proxy and before changing production router sites.

**IPRoyal (recommended first test):** [docs/runbooks/iproyal-isp-proxy-setup.md](../../docs/runbooks/iproyal-isp-proxy-setup.md) — purchase → URL format → local → Key Vault → Melibox.

**Spec:** [docs/SPECS/PROXY_ROTATION_SPEC.md](../../docs/SPECS/PROXY_ROTATION_SPEC.md)  
**Readiness:** [.agent/commands/proxy-readiness.md](../commands/proxy-readiness.md)

## Preconditions

- [ ] Credentials in Key Vault (`CREDENTIAL_MELIBOX_*`, etc.) — never commit values
- [ ] `PROXY_URLS` stored as Key Vault secret `proxy-urls` (JSON array, one URL)
- [ ] If `PROXY_ROTATION_ENABLED=true` and `PROXY_FAIL_CLOSED=true`, `PROXY_URLS` must be non-empty or the worker will not start

## Phase A — Connectivity (no supplier sites)

```bash
cd scrapers
uv run python scripts/proxy_readiness_check.py --proxy-url 'http://USER:PASS@HOST:PORT'
# or after Container App secrets:
uv run python scripts/proxy_readiness_check.py --from-env
```

Accept: Playwright OK, egress IP matches purchased IP.

## Phase B — Per-site smoke (local or worker shell)

```bash
PROXY_ROTATION_ENABLED=true \
PROXY_URLS='["http://USER:PASS@HOST:PORT"]' \
PROXY_FAIL_CLOSED=true \
PROXY_AFFINITY_ENABLED=true \
PROXY_STATE_PER_IDENTITY=true \
uv run python scripts/proxy_site_smoke.py --from-env
```

Order of interpretation:

| Site | Success signal | If still `blocked` |
|------|----------------|---------------------|
| `melibox` | `success` with priced rows | Wrong IP type, credentials, or supplier block |
| `pecadireta`, `gm`, `vw`, `eu`, `ml` | `success` or known `not_found` | Regression — do not enable prod router |
| `goparts`, `procurapecas` | Any non-timeout | Cloudflare may need unlocker / API path |

Report: `docs/validation/latest_proxy_site_smoke.json`

## Phase C — Production secrets

1. Set Container App secrets (`proxy-urls`, `proxy-rotation-enabled`).
2. Restart API + worker revision.
3. Clear stale `browser_states/*` created on Azure egress (or use new `_{proxy_identity}_state.json` files).
4. Re-run readiness + one Melibox job via API.

## Phase D — Re-enable archived scrapers (manual)

Only after Phase B documents `success` or acceptable status:

1. Move site from `ARCHIVED_SCRAPER_REGISTRY` to `SCRAPER_REGISTRY` in `src/scrapers/__init__.py`.
2. Add site to router `DEFAULT_SITES` or `CDP_SCRAPER_SITES` env (platform `n8n/src/formatar_payload_scraper.js`).
3. Run `make test`, proxy smoke again, 5-SKU production audit.

**Do not** assume all four archived/blocked sources recover with ISP proxy alone (Cloudflare Turnstile on GoParts / Procura Peças).

## Phase E — Router / docs

- Update [docs/MAINTENANCE_CHECKPOINT.md](../../docs/MAINTENANCE_CHECKPOINT.md) and [.agent/memory/implementation-state.md](../memory/implementation-state.md) with provider name (no secrets) and date validated.
- Optional: add `melibox` to router default sites only after Melibox prod smoke passes.

## Completion

- [ ] `make test lint` in `scrapers/`
- [ ] Platform `.agent/memory/implementation-state.md` if prod behavior changed
- [ ] No n8n publish without user approval
