# ADR-0004: Scraper cache enforced in worker, not n8n

**Status:** Accepted  
**Date:** 2026-05-26

## Context

Repeat SKU+site requests should avoid Playwright to reduce bot risk and cost.

## Decision

- Router always sends `force_refresh: false` on `POST /api/v1/jobs`.
- Cache TTL (24h success/no_price) lives in scraper API + worker (Redis DB 1, PostgreSQL fallback).
- n8n does not pre-filter sites or bypass cache.

## Consequences

- Stale data fixes require understanding cache TTLs, not router-only changes.
- `force_refresh=true` remains an API escape hatch for ops, not default dispatch.
