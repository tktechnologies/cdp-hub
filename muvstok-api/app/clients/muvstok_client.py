from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.domain.muvstok_api import extract_access_token, extract_demand_rows, is_auth_failure


class MuvstokClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def authenticate(self, username: str, password: str) -> str:
        login_url = self._settings.muvstok_login_path.strip()
        if not login_url:
            msg = "MUVSTOK_LOGIN_PATH is not configured."
            raise ValueError(msg)
        payload = {"user": username.strip(), "password": password}
        async with httpx.AsyncClient(timeout=self._settings.muvstok_timeout_seconds) as client:
            response = await client.post(login_url, json=payload)
            response.raise_for_status()
            token = extract_access_token(response.json())
            if not token:
                msg = "API Diversos auth response did not include an access token."
                raise ValueError(msg)
            return token

    async def fetch_sku(self, sku: str, token: str) -> tuple[list[dict[str, Any]], int]:
        """Return demand rows and HTTP status code (404 means not found)."""
        demand_url = self._settings.muvstok_base_url.strip()
        if not demand_url:
            msg = "MUVSTOK_BASE_URL is not configured."
            raise ValueError(msg)
        async with httpx.AsyncClient(timeout=self._settings.muvstok_timeout_seconds) as client:
            response = await client.get(
                demand_url,
                params={"sku": sku},
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 404:
                return [], 404
            if is_auth_failure(response.status_code, response.text):
                return [], response.status_code
            response.raise_for_status()
            return extract_demand_rows(response.json()), response.status_code

    def build_product_url(self, sku: str) -> str:
        base = self._settings.muvstok_base_url.strip().rstrip("/")
        return f"{base}/?{urlencode({'sku': sku})}"
