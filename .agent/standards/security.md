# Security (Platform)

## Non-negotiables

- Production secrets: Azure Key Vault `cdp-scrapers-kv-prod` — never commit values.
- API auth: `X-API-Key` on protected endpoints.
- n8n callbacks: `X-Webhook-Secret` / env-based secrets — never in workflow JSON or agent memory.
- Never commit `.env`, browser states, tokens, connection strings, or customer data.

## Callbacks

- Callback URLs must be public HTTPS (StokAPI validates; scraper uses configured URLs).
- Coordinate webhook path or secret changes across API, worker, and receiver workflow.

## Service detail

- StokAPI: [muvstok-api/.agent/standards/security-and-secrets.md](../../muvstok-api/.agent/standards/security-and-secrets.md)
- Scraper: Key Vault + env in `scrapers/src/config.py`
