# Google Sheets Reporting Maintenance Prompt

Copy this into a new chat for dashboard, formula, pivot, `.xlsx`, or sheet
receiver mapping work.

```text
You are working on CDP Google Sheets reporting across Scraper + API Diversos + n8n.

Start by reading:
1. AGENTS.md
2. .agent/rules/google-sheets.md
3. .agent/knowledge/google-sheets-reporting.md
4. docs/n8n/DATA_CONTRACTS.md
5. Service AGENTS.md only if changing receiver code:
   - scrapers/AGENTS.md for cdp_scraper
   - muvstok-api/AGENTS.md for cdp_stokapi

Rules:
- Found-price success is only FOUND_PRICE + has_valid_price=true.
- Row existence in Detalhado is not success.
- Keep NO_PRICE, NOT_FOUND, BLOCKED, TIMEOUT, ERROR, and NOT_QUERIED separate.
- Captcha/anti-bot/403/access denied is BLOCKED, not NOT_FOUND.
- Seller columns are vendedor, uf, empresa, cnpj; never write estado.
- Use API Diversos as the user-facing stock source name.
- Do not mutate production spreadsheets or publish n8n without explicit approval.

Before final:
- Summarize formulas/mappings changed.
- State which denominator each KPI uses.
- Run relevant local JSON/script/tests, or explain why skipped.
```
