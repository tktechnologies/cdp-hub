# n8n Receiver Agent

## Ownership

`cdp_scraper` callback receiver behavior: flattening, Sheets updates,
Telegram/email result formatting, and scraper callback contract alignment.

## Read First

- [../skills/n8n-audit/SKILL.md](../skills/n8n-audit/SKILL.md)
- [../skills/n8n-release-preflight/SKILL.md](../skills/n8n-release-preflight/SKILL.md)
- [../../../.agent/boundaries/n8n.md](../../../.agent/boundaries/n8n.md)
- `../../../n8n/workflows/cdp_scraper.json`
- `../../../n8n/lib/scraper_telegram_notification.js`

## Expected Output

- Receiver nodes/helpers changed.
- Callback fields consumed and contract impact.
- Whether inject/preflight was run.

## Boundaries

Do not edit `n8n/src/` router dispatch without switching to platform
`n8n-router-sync`. Do not publish live n8n without explicit user approval.
