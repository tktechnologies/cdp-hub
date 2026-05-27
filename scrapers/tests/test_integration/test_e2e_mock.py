"""E2E: submit job -> poll -> verify results. Uses mock scraper + SQLite."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.integration
class TestE2EMockPipeline:

    @pytest.mark.asyncio
    async def test_submit_and_get_results(self, api_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            # Submit job with known mock SKU
            resp = await c.post(
                "/api/v1/jobs",
                json={"items": [{"sku": "93338835", "brand": "GM"}], "sites": ["gm"]},
                headers=api_headers,
            )
            assert resp.status_code == 200
            job_id = resp.json()["job_id"]

            # Poll until done
            for _ in range(30):
                await asyncio.sleep(0.1)
                poll = await c.get(f"/api/v1/jobs/{job_id}", headers=api_headers)
                data = poll.json()
                if data["status"] in ("completed", "partial", "failed"):
                    break

            assert data["status"] in ("completed", "partial")
            assert len(data["results"]) == 1
            part = data["results"][0]["site_results"][0]["results"][0]
            assert part["price"] == 45.90
            assert part["exact_match"] is True

    @pytest.mark.asyncio
    async def test_unknown_sku(self, api_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/api/v1/jobs",
                json={"items": [{"sku": "UNKNOWN999", "brand": "GM"}], "sites": ["gm"]},
                headers=api_headers,
            )
            job_id = resp.json()["job_id"]

            for _ in range(30):
                await asyncio.sleep(0.1)
                poll = await c.get(f"/api/v1/jobs/{job_id}", headers=api_headers)
                data = poll.json()
                if data["status"] in ("completed", "partial", "failed"):
                    break

            assert data["results"][0]["total_results"] == 0
