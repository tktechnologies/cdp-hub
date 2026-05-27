.PHONY: help dev dev-up dev-down dev-logs dev-scraper dev-stokapi dev-full \
	compose-up compose-down compose-full compose-logs \
	test test-all test-scraper test-stokapi \
	lint lint-all format-all check-muvstok \
	setup clean \
	inject-n8n sync-n8n-prep sync-n8n \
	smoke-cache interview-demo \
	migrate-scraper migrate-stokapi \
	bicep-build bicep-what-if bicep-validate

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
COMPOSE := docker compose -f $(ROOT)docker-compose.yml
SCRAPERS := $(ROOT)scrapers
STOKAPI := $(ROOT)muvstok-api

.DEFAULT_GOAL := help

help: ## List platform targets
	@grep -E '^[a-zA-Z0-9_.-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Local development ───────────────────────────────────────────────────────
dev: dev-up ## Start Postgres + Redis (host-native APIs)
	@echo "Deps ready. Start APIs on host:"
	@echo "  make dev-scraper   # scraper :8000"
	@echo "  make dev-stokapi   # stokapi :8001"

dev-up: ## docker compose up deps (postgres + redis)
	$(COMPOSE) up -d postgres redis

dev-down: ## Stop all compose services
	$(COMPOSE) --profile full down

dev-logs: ## Follow compose logs
	$(COMPOSE) --profile full logs -f

dev-scraper: dev-up ## Run scraper API on host (:8000)
	$(MAKE) -C $(SCRAPERS) dev

dev-stokapi: dev-up ## Run StokAPI on host (:8001)
	cd $(STOKAPI) && API_PORT=8001 uv run uvicorn app.main:app --reload --port 8001

dev-full: ## Docker: postgres, redis, scraper + stokapi stacks
	$(COMPOSE) --profile full up -d --build

compose-up: dev-up ## Alias for dev-up

compose-down: dev-down ## Alias for dev-down

compose-full: dev-full ## Alias for dev-full

compose-logs: dev-logs ## Alias for dev-logs

setup: ## Copy env examples and start deps
	@test -f $(SCRAPERS)/.env || cp -n $(SCRAPERS)/.env.example $(SCRAPERS)/.env || true
	@test -f $(STOKAPI)/.env || cp -n $(STOKAPI)/.env.example $(STOKAPI)/.env || true
	@test -f $(ROOT).env || cp -n $(ROOT).env.example $(ROOT).env || true
	$(MAKE) dev-up
	@echo "Edit scrapers/.env and muvstok-api/.env, then: make migrate-scraper"

# ─── Tests ───────────────────────────────────────────────────────────────────
test: test-scraper ## Default test: scraper suite

test-all: test-scraper test-stokapi ## Run all service test suites

test-scraper: ## Scraper pytest
	$(MAKE) -C $(SCRAPERS) test

test-stokapi: ## StokAPI pytest (may be empty locally)
	cd $(STOKAPI) && UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v --tb=short 2>/dev/null || $(MAKE) -C $(STOKAPI) test

# ─── Lint / format ───────────────────────────────────────────────────────────
lint: lint-all ## Alias for lint-all

lint-all: ## Ruff + mypy for scraper and StokAPI
	$(MAKE) -C $(SCRAPERS) lint
	$(MAKE) check-muvstok

format-all: ## Ruff format both services
	$(MAKE) -C $(SCRAPERS) format
	cd $(STOKAPI) && uv run ruff format . && uv run ruff check --fix .

check-muvstok: ## StokAPI ruff + mypy
	cd $(STOKAPI) && UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . && UV_CACHE_DIR=/tmp/uv-cache uv run mypy app

check-specs: ## StokAPI required spec files
	cd $(STOKAPI) && ./scripts/check_specs.sh

# ─── Database migrations ─────────────────────────────────────────────────────
migrate-scraper: dev-up ## Alembic upgrade (scraper)
	$(MAKE) -C $(SCRAPERS) migrate

migrate-stokapi: dev-up ## Alembic upgrade (StokAPI)
	cd $(STOKAPI) && uv run alembic upgrade head

# ─── n8n router sync ─────────────────────────────────────────────────────────
inject-n8n: ## Inject shared JS into workflow JSON (no publish)
	python3 $(ROOT)scripts/sync_workflow_code_from_shared.py

sync-n8n-prep: inject-n8n ## Prepare workflows locally (inject only)
	@echo "Review n8n/ changes. Publish with: make sync-n8n (requires approval)"

sync-n8n: ## Inject + push to live n8n (requires user approval)
	bash $(ROOT)scripts/sync-all-n8n.sh

# ─── Integration smoke / demos ───────────────────────────────────────────────
smoke-cache: ## Dual-pipeline smoke (production APIs)
	bash $(ROOT)scripts/smoke_dual_pipeline.sh

interview-demo: ## Scraper Playwright interview demo
	$(MAKE) -C $(SCRAPERS) interview-demo ARGS="$(ARGS)"

# ─── Infrastructure (no deploy) ──────────────────────────────────────────────
bicep-build: ## Compile root infra/main.bicep
	az bicep build --file $(ROOT)infra/main.bicep --stdout > /tmp/cdp-platform-main.json
	@echo "Wrote /tmp/cdp-platform-main.json"

bicep-what-if: ## What-if for platform stack (no changes applied)
	az deployment group what-if \
		--resource-group $${AZURE_RESOURCE_GROUP:-automation} \
		--template-file $(ROOT)infra/main.bicep \
		--parameters @$(ROOT)infra/main.parameters.example.json

bicep-validate: bicep-build ## Build Bicep only (validation)

# ─── Cleanup ─────────────────────────────────────────────────────────────────
clean: ## Remove caches in both services
	$(MAKE) -C $(SCRAPERS) clean
	find $(STOKAPI) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(STOKAPI)/.pytest_cache $(STOKAPI)/.mypy_cache 2>/dev/null || true
