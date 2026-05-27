# Security And Secrets

## Rules

- Store Muvstok tokens and credentials in Azure Key Vault.
- Store only Key Vault references and metadata in PostgreSQL.
- Never log tokens, API keys, passwords, connection strings, `Authorization` headers, Key Vault values, or callback HMAC secrets.
- Use Managed Identity in Azure.
- Validate callback URLs to reduce SSRF risk.

## API Clients

Version 1 may start with configured API keys. The application derives a short non-secret fingerprint for client scoping. Production should move to hashed API keys in `api_clients`, with rotation and revocation.

## Callback Security

Callbacks should use HTTPS and should support an HMAC signature header once the callback contract is finalized.

## Redis Security

Redis must require authentication, run on private network paths where possible, and use persistence settings appropriate to its deployment model.
