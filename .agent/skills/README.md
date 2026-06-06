# Platform skills

Each skill folder should contain a `SKILL.md` with YAML frontmatter
(`name`, `description`) and concise procedural instructions. Keep detailed
facts in `memory/` or `knowledge/` instead of copying them into every skill.

| Skill | When |
|-------|------|
| [n8n-router-sync/SKILL.md](n8n-router-sync/SKILL.md) | Edit `n8n/src/`, inject, `make sync-n8n` |
| [dual-pipeline-change/SKILL.md](dual-pipeline-change/SKILL.md) | Change `.analisar` / `.sku` / dual dispatch behavior |
| [google-sheets-dashboard/SKILL.md](google-sheets-dashboard/SKILL.md) | Audit or improve Sheets dashboards, formulas, reports, pivots, `.xlsx` exports |

**Service skills:** descend to `scrapers/.agent/skills/` or `muvstok-api/.agent/skills/` for Playwright, cache, API Diversos/StokAPI worker, migrations, etc.
