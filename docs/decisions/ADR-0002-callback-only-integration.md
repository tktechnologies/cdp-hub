# ADR-0002: Callback-only worker integration with n8n

**Status:** Accepted  
**Date:** 2026-05-26

## Context

Workers must notify n8n when jobs complete so Sheets and Telegram update.

## Decision

Workers POST JSON to stable n8n webhooks only:

- Scraper → `scraper-result` (`cdp_scraper`)
- StokAPI → `muvstok-result` (`cdp_stokapi`)

No direct worker-to-worker calls. No n8n Execute Workflow for StokAPI production dispatch (inline HTTP in router).

## Consequences

- Callback payloads are versioned in `contracts/` and service Pydantic models.
- Webhook path or secret changes require coordinated deploy of API, worker, and receiver workflow.
- Notification context for Telegram travels in `callback_url` query parameters where the API does not carry arbitrary metadata.
