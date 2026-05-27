# Security And Secrets

## Non-Negotiables

- Never log raw tokens, API keys, passwords, connection strings, authorization headers, Key Vault values, or callback HMAC secrets.
- Never store raw Muvstok tokens or credentials in PostgreSQL.
- Store Muvstok secrets in Azure Key Vault and only store references or metadata in PostgreSQL.
- Use Managed Identity in Azure where possible.
- Validate callback URLs as public HTTPS and keep improving SSRF protection.

## Current Auth State

- Protected endpoints use `X-API-Key`.
- Version 1 currently supports configured bootstrap keys through `API_KEYS`.
- The app derives a short non-secret fingerprint for configured keys.
- Production should move to hashed API keys in `api_clients` with rotation and revocation.

## Callback Security

- Callback URLs must be public HTTPS.
- Future callback payloads should support HMAC signatures once the contract is finalized.
- Callback failures must not delete raw stored Muvstok data.

## Redis Security

- Redis must require authentication in deployed environments.
- Prefer private network paths.
- Define persistence, backup, monitoring, and restart behavior before relying on self-hosted Redis.
