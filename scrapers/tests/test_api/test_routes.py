"""Tests for API routes."""


import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import settings
from src.main import app
from src.models.schemas import JobStatus, ScrapeJobResponse, SiteId


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest_asyncio.fixture
async def client(transport):
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def api_key():
    return settings.api_key


class TestHealthEndpoint:
    async def test_health_no_auth_required(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_returns_version(self, client):
        response = await client.get("/api/v1/health")
        assert "version" in response.json()


class TestAuthMiddleware:
    async def test_jobs_requires_api_key(self, client):
        response = await client.post("/api/v1/jobs", json={"items": [{"sku": "test"}]})
        assert response.status_code == 422 or response.status_code == 401

    async def test_invalid_api_key_rejected(self, client):
        response = await client.post(
            "/api/v1/jobs",
            json={"items": [{"sku": "test"}]},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401


class TestRootEndpoint:
    async def test_root_returns_service_info(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "cdp-scraper"


class TestTelegramDemoEndpoint:
    async def test_demo_telegram_submits_job_with_routed_callback(
        self, client, api_key, monkeypatch
    ):
        captured = {}

        async def fake_submit_job(request):
            captured["request"] = request
            return ScrapeJobResponse(
                job_id="demo-job-1",
                status=JobStatus.PENDING,
                total_items=len(request.items),
                sites=request.sites,
                estimated_duration_seconds=45,
            )

        monkeypatch.setattr("src.services.orchestrator.orchestrator.submit_job", fake_submit_job)
        monkeypatch.setattr(
            settings,
            "demo_callback_url",
            "https://n8n.example.test/webhook/scraper-result?source=meeting",
        )

        response = await client.post(
            "/api/v1/demo/telegram",
            json={
                "chat_id": "123456",
                "items": [{"sku": "06K907811B", "brand": "VW"}],
                "sites": ["gm", "vw"],
            },
            headers={"X-API-Key": api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "demo-job-1"
        assert data["telegram_chat_id"] == "123456"
        assert "source=meeting" in data["callback_url"]
        assert "notify=telegram" in data["callback_url"]
        assert "chat_id=123456" in data["callback_url"]
        assert captured["request"].callback_url == data["callback_url"]
        assert captured["request"].sites == [SiteId.GM, SiteId.VW]
