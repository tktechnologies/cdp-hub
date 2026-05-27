# Workflow: Local Development

## Goal
Run the scraper API locally with repeatable checks.

## Steps
1. Install dependencies and browsers:
   ```bash
   make setup
   ```
2. Configure `.env` with API key and site credentials.
3. Run database migrations:
   ```bash
   make migrate
   ```
4. Start the API:
   ```bash
   make dev
   ```
5. Use `MOCK_SCRAPERS=true` when you intentionally want mock GM responses.
6. Validate with:
   ```bash
   make test
   make lint
   ```

## Notes
- CDP-owned n8n workflow exports live under `n8n/`; keep them aligned with the API and callback docs when workflow behavior changes.
- Keep unrelated workflow automation assets outside this repo.
- Do not commit `.env`, browser states, authenticated screenshots, API keys, webhook secrets, or real customer payloads.
