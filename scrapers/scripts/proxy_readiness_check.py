#!/usr/bin/env python3
"""Validate scraper proxy readiness without touching supplier websites."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings  # noqa: E402
from src.utils.proxy_manager import ProxyEndpoint  # noqa: E402

DEFAULT_IP_URL = "https://api.ipify.org?format=json"


@dataclass
class CheckResult:
    proxy: str
    http_ok: bool | None
    playwright_ok: bool
    egress_ip: str | None
    error: str | None = None


def mask_proxy_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.username and not parsed.password:
        return raw_url
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"***:***@{host}{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def proxy_urls_from_args(args: argparse.Namespace) -> list[str]:
    urls = list(args.proxy_url or [])
    if args.from_env:
        urls.extend(settings.proxy_urls)
    return [url.strip() for url in urls if url.strip()]


async def check_httpx(proxy_url: str, ip_url: str) -> tuple[bool | None, str | None, str | None]:
    parsed = urlparse(proxy_url)
    if parsed.scheme not in {"http", "https"}:
        return None, None, "httpx check skipped for non-HTTP proxy scheme"

    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=20.0, follow_redirects=True) as client:
            response = await client.get(ip_url)
            response.raise_for_status()
            payload = response.json()
            return True, str(payload.get("ip") or response.text.strip()), None
    except Exception as exc:
        return False, None, str(exc)


async def check_playwright(proxy_url: str, ip_url: str) -> tuple[bool, str | None, str | None]:
    endpoint = ProxyEndpoint.from_url(proxy_url)
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(proxy=endpoint.to_playwright())
            page = await context.new_page()
            await page.goto(ip_url, wait_until="domcontentloaded", timeout=30_000)
            body = (await page.text_content("body")) or ""
            await context.close()
            await browser.close()

        try:
            payload = json.loads(body)
            return True, str(payload.get("ip") or body.strip()), None
        except json.JSONDecodeError:
            return True, body.strip(), None
    except Exception as exc:
        return False, None, str(exc)


async def check_proxy(proxy_url: str, ip_url: str) -> CheckResult:
    masked = mask_proxy_url(proxy_url)
    http_ok, http_ip, http_error = await check_httpx(proxy_url, ip_url)
    playwright_ok, playwright_ip, playwright_error = await check_playwright(proxy_url, ip_url)
    return CheckResult(
        proxy=masked,
        http_ok=http_ok,
        playwright_ok=playwright_ok,
        egress_ip=playwright_ip or http_ip,
        error=playwright_error or http_error,
    )


async def main_async(args: argparse.Namespace) -> int:
    urls = proxy_urls_from_args(args)
    if not urls:
        print(
            "No proxy URLs provided. Use --proxy-url or --from-env with PROXY_URLS configured.",
        )
        return 2

    results = [await check_proxy(url, args.ip_url) for url in urls]
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2, sort_keys=True))
    else:
        for result in results:
            http_status = "skipped" if result.http_ok is None else "ok" if result.http_ok else "failed"
            playwright_status = "ok" if result.playwright_ok else "failed"
            print(f"proxy={result.proxy}")
            print(f"  httpx={http_status}")
            print(f"  playwright={playwright_status}")
            print(f"  egress_ip={result.egress_ip or '-'}")
            if result.error:
                print(f"  error={result.error}")

    return 0 if all(result.playwright_ok for result in results) else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether proxy URLs work with the scraper Playwright stack.",
    )
    parser.add_argument(
        "--proxy-url",
        action="append",
        help="Proxy URL, e.g. http://user:pass@host:12323 or socks5://user:pass@host:12324.",
    )
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Also read URLs from PROXY_URLS via scraper settings.",
    )
    parser.add_argument(
        "--ip-url",
        default=DEFAULT_IP_URL,
        help="Neutral IP echo URL. Defaults to api.ipify.org.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser.parse_args()


def main() -> int:
    return asyncio.run(main_async(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
