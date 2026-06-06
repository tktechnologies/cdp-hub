# ADR-0001: Monorepo with two independent APIs

**Status:** Accepted  
**Date:** 2026-05-26

## Context

CDP needs public scrape data and API Diversos/StokAPI stock data for the same
SKU sets, triggered from Telegram/Sheets via n8n.

## Decision

Maintain **two separate Python services** in one monorepo:

- `scrapers/` — Playwright scraping, Celery, scrape cache
- `muvstok-api/` — Muvstok ingestion, Redis Streams worker

A single n8n router (`cdp_router`) orchestrates both; there is **no shared Python package** between them.

## Consequences

- Clear ownership and deploy boundaries per service.
- Contract changes require coordinated updates in `contracts/` and both APIs when shapes overlap at the router.
- Agents must pick the correct tier before editing code.
