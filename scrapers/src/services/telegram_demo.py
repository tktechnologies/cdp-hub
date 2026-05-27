"""Telegram-routed demo job submission."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.config import settings
from src.models.schemas import (
    ScrapeJobRequest,
    TelegramDemoJobRequest,
    TelegramDemoJobResponse,
)
from src.services.orchestrator import orchestrator


class MissingDemoCallbackUrlError(Exception):
    """Raised when no callback URL is configured for a Telegram demo job."""


def append_query_params(url: str, params: dict[str, str]) -> str:
    """Append routing query parameters while preserving existing URL params."""
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({key: value for key, value in params.items() if value})
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )


async def submit_telegram_demo_job(
    request: TelegramDemoJobRequest,
) -> TelegramDemoJobResponse:
    """Submit a small demo job with completion routed to Telegram via n8n."""
    base_callback_url = request.callback_url or settings.demo_callback_url
    if not base_callback_url:
        raise MissingDemoCallbackUrlError()

    callback_url = append_query_params(
        base_callback_url,
        {
            "notify": "telegram",
            "chat_id": request.chat_id,
            "ad_hoc": "true" if request.ad_hoc else "false",
        },
    )
    job_request = ScrapeJobRequest(
        items=request.items,
        sites=request.sites,
        callback_url=callback_url,
        priority=request.priority,
    )
    response = await orchestrator.submit_job(job_request)
    return TelegramDemoJobResponse(
        **response.model_dump(),
        callback_url=callback_url,
        telegram_chat_id=request.chat_id,
    )
