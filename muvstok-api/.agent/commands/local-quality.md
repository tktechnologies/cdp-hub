# Local Quality Commands

Use these as fast feedback before Azure validation.

## Specs

```bash
bash scripts/check_specs.sh
```

Expected output: `All required specs exist.`

## Ruff

```bash
uv run ruff check .
```

Use after Python edits.

## Mypy

```bash
uv run mypy .
```

Use after typed Python changes.

## Pytest

```bash
uv run pytest
```

Current state: unit, service, and contract tests exist. Passing local tests are useful feedback, but Azure-hosted validation is still required when production-like behavior is in scope.
