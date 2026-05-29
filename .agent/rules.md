# CDP Platform — Agent Rules

Tier 1 rules. Service-specific rules live in `scrapers/.agent/rules.md` and `muvstok-api/.agent/rules.md`.

## Read order

1. This file
2. [index.md](index.md)
3. [boundaries/services.md](boundaries/services.md) + [boundaries/n8n.md](boundaries/n8n.md)
4. [memory/implementation-state.md](memory/implementation-state.md)
5. Descend to Tier 2 when editing service code

## Architecture

- **Two APIs, one router:** Scraper and StokAPI are independent HTTP services; `cdp_router` coordinates them.
- **No shared Python** between `scrapers/` and `muvstok-api/`.
- **Callbacks only** connect workers to n8n (webhooks + secrets).

## n8n (non-negotiable)

1. Production dispatch **only** in `cdp_router` — inline HTTP for both arms.
2. Edit router Code in `n8n/src/`; inject before committing `cdp_router.json`.
3. Stable webhooks: `scraper-result`, `muvstok-result`.
4. `.analisar` and `.sku`: all valid SKUs pass through by default; optional sampling is controlled by `CDP_DISPATCH_SAMPLE_SIZE`.
5. Never publish live n8n without explicit user approval.

## Secrets

- Key Vault `cdp-scrapers-kv-prod` for production.
- Never commit secrets to workflow JSON, agent memory, or chat.

## Documentation

- Platform truth: `docs/` at monorepo root.
- Link instead of copying full architecture into service repos.
- Behavior changes update specs/docs in the **owning** tier.

## AIOX

`.aiox-core/` and top-level `.agent/workflows/*.md` (analyst, dev, pm, …) are IDE tooling — not CDP runtime.
