# EU Imports Scraper

**Site ID:** `eu`  
**Code:** `src/scrapers/eu_imports.py`  
**Source:** `https://export.fastparts.is`

## Story

EU Imports is a table, not a marketplace. It is the foreign-currency source and
therefore must preserve USD/EUR instead of pretending everything is BRL.
Mercedes has a special rule: remove the first character before searching.

## What We Want

- Navigate to `https://export.fastparts.is`.
- Fill `input[placeholder*='part code']`, press Enter.
- Extract table rows: manufacturer, part number, delivery, price, quantity when
  visible.
- Preserve source currency.

## Current DOM Map

- Search input: `input[placeholder*='part code']`.
- Rows: `tr`, `.p-datatable-row`.
- Price text: `$`, `€`, or `EUR` in row text.
- Manufacturer often appears in row text, e.g. `VAG`.

## Known Evidence

2026-05-13 all-scraper probe:

- `06K907811B` -> `success`, USD 292.13, VAG rows.
- `5U6867287Y20` -> `not_found`.

## Failure Modes

- Duplicate rows can appear.
- Delivery extraction is currently coarse.
- Placeholder text may drift in Angular updates.

## Agent Moves

- Do not compare USD/EUR against BRL for `best_price` unless conversion exists.
- Keep Mercedes normalization covered by tests.
- If the input is missing, inspect Angular render timing and placeholder text.
