# Workflow: Scraper Release Check

## Goal
Verify that a scraper/API change is ready to ship.

## Checklist
1. Confirm `src/scrapers/__init__.py` registry has no duplicate or unintended entries.
2. Confirm default site lists in `src/models/schemas.py` match the intended supported sites.
3. Run scraper tests:
   ```bash
   uv run pytest tests/test_scrapers -v
   ```
4. Run API and orchestrator tests:
   ```bash
   uv run pytest tests/test_api tests/test_services/test_orchestrator.py -v
   ```
5. Run integration tests when persistence or job flow changed:
   ```bash
   uv run pytest tests/test_integration -v
   ```
6. Run quality checks:
   ```bash
   uv run ruff check src tests
   uv run mypy src
   ```
7. Search for accidental artifacts:
   ```bash
   rg -n "S[t]ripe|C[l]erk|\\.[a]gents|docs/T[K]|0_[r]outer|1_[c]omments|spec1-[i]nstagram|file:/[/]/|docs/video_[a]nalysis|demo_[p]resentation|europe\\.py|S[T]UB" .agent docs src tests scripts README.md
   rg -n "print\\(" src
   ```

## Done When
- Tests pass or documented failures are understood.
- No secret material or browser artifacts are present.
- `.agent` instructions still match the code.
