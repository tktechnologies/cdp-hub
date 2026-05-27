.PHONY: dev worker test lint format migrate docker-up docker-down clean local-db-up local-db-reset validate-local-preflight validate-local-scrapers demo interview-demo db-inspect bicep-build bicep-what-if

# ─── Development ────────────────────────────────────────
dev:
	docker compose up -d postgres redis
	uvicorn src.main:app --reload --port 8000

worker:
	docker compose up -d postgres redis
	JOB_EXECUTION_BACKEND=celery celery -A src.celery_app.celery_app worker --loglevel=INFO --concurrency=$${CELERY_WORKER_CONCURRENCY:-1}

dev-full:
	docker compose up -d

# ─── Testing ────────────────────────────────────────────
test:
	UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v --tb=short

test-cov:
	UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

test-watch:
	UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v --tb=short -f

test-scrape-cache:
	UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests/test_services/test_scrape_cache.py -v

smoke-scrape-cache-local:
	chmod +x scripts/test_scrape_cache_local.sh
	./scripts/test_scrape_cache_local.sh

# ─── Code Quality ───────────────────────────────────────
lint:
	UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/ tests/ scripts/
	UV_CACHE_DIR=/tmp/uv-cache uv run mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# ─── Database ───────────────────────────────────────────
migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"

local-db-up:
	docker compose up -d postgres redis

local-db-reset:
	docker compose down -v
	docker compose up -d postgres redis
	sleep 5
	alembic upgrade head

validate-local-preflight:
	pytest -v
	ruff check src tests scripts alembic
	mypy src || true

validate-local-scrapers:
	python scripts/validate_local_scrapers.py --manifest $${MANIFEST:-docs/validation/local_scraper_manifest.local.json}

demo:
	MOCK_SCRAPERS=false PROXY_ROTATION_ENABLED=false UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/demo_scraper_runs.py $(ARGS)

interview-demo:
	PLAYWRIGHT_HEADLESS=false MOCK_SCRAPERS=false PROXY_ROTATION_ENABLED=false \
		UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/interview_scraper_demo.py $(ARGS)

# Melibox + Royal IP BR residential proxy (set PROXY_URLS in .env before the meeting).
interview-demo-melibox:
	PLAYWRIGHT_HEADLESS=false MOCK_SCRAPERS=false PROXY_ROTATION_ENABLED=true \
		MELIBOX_SKU_DELAY_MIN=0 MELIBOX_SKU_DELAY_MAX=0 \
		UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/interview_scraper_demo.py --sites melibox $(ARGS)

db-inspect:
	UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev python scripts/inspect_scrape_db.py $(ARGS)

bicep-build:
	az bicep build --file infra/main.bicep --stdout > /tmp/cdp-scraper-main.bicep.json

bicep-what-if:
	az deployment group what-if --resource-group automation --template-file infra/main.bicep --parameters @$${PARAMETERS:-infra/main.parameters.local.json}

# ─── Docker ─────────────────────────────────────────────
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f scraper-api

docker-rebuild:
	docker compose build --no-cache scraper-api
	docker compose up -d scraper-api

# ─── Utilities ──────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache

install:
	pip install -e ".[dev]"
	playwright install chromium

setup: install
	cp -n .env.example .env || true
	docker compose up -d postgres redis
	sleep 3
	alembic upgrade head
	@echo "✅ Setup complete. Edit .env with real credentials, then run: make dev"
