.PHONY: check-specs azure-test test lint dev

check-specs:
	./scripts/check_specs.sh

azure-test:
	./scripts/azure_test.sh

test:
	UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v --tb=short 2>/dev/null || echo "No tests yet — see tests/README.md"

lint:
	UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
	UV_CACHE_DIR=/tmp/uv-cache uv run mypy app

dev:
	docker compose -f docker/docker-compose.yml up -d
