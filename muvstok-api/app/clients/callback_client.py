from typing import Any

import httpx

from app.core.config import Settings


class CallbackClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def post_callback(
        self,
        callback_url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._settings.callback_timeout_seconds) as client:
            response = await client.post(callback_url, json=payload, headers=headers)
            response.raise_for_status()
            return response
