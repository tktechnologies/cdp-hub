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

Current state: tests are not implemented beyond `tests/README.md`, so passing or empty local tests are not enough for done.
