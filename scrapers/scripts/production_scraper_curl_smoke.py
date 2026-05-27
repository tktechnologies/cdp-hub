"""Run production scraper smoke checks through the public API using curl.

Environment:
  API_BASE_URL       Required. Example: https://scrapers-api.example.com
  API_KEY            Required. Sent as X-API-Key.
  N8N_BASE_URL       Optional. If set, the script checks N8N health too.
  N8N_HEALTH_PATH    Optional. Defaults to /healthz.

Examples:
  API_BASE_URL=https://... API_KEY=... python scripts/production_scraper_curl_smoke.py

  API_BASE_URL=https://... API_KEY=... \
    python scripts/production_scraper_curl_smoke.py \
    --manifest docs/validation/production_scraper_curl_cases.example.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ACTIVE_SITES = {"gm", "ml", "vw", "eu", "pecadireta", "melibox"}


@dataclass(frozen=True)
class SmokeCase:
    id: str
    site: str
    sku: str
    brand: str = ""
    expected_statuses: tuple[str, ...] = ("success",)
    require_exact: bool = True
    require_price: bool = True
    expected_currency: str | None = None


DEFAULT_CASES: tuple[SmokeCase, ...] = (
    SmokeCase("gm-known", "gm", "22781768", "GM", expected_currency="BRL"),
    SmokeCase("ml-known", "ml", "06K907811B", expected_currency="BRL"),
    SmokeCase("vw-known", "vw", "5U6867287Y20", "VW", expected_currency="BRL"),
    SmokeCase("eu-known", "eu", "06K907811B", "VW", expected_currency="USD"),
    SmokeCase(
        "pecadireta-known",
        "pecadireta",
        "06K907811B",
        expected_statuses=("success", "no_price"),
        require_price=False,
        expected_currency="BRL",
    ),
)


def _normalize_sku(value: str) -> str:
    return re.sub(r"[\s\-./]", "", value).upper()


def _load_cases(path: Path | None) -> list[SmokeCase]:
    if path is None:
        return list(DEFAULT_CASES)

    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise RuntimeError(f"Manifest {path} must contain a non-empty cases list.")

    cases: list[SmokeCase] = []
    for raw in raw_cases:
        site = str(raw["site"])
        if site not in ACTIVE_SITES:
            raise RuntimeError(f"Unsupported active site in smoke manifest: {site}")
        cases.append(
            SmokeCase(
                id=str(raw["id"]),
                site=site,
                sku=str(raw["sku"]),
                brand=str(raw.get("brand", "")),
                expected_statuses=tuple(raw.get("expected_statuses", ["success"])),
                require_exact=bool(raw.get("require_exact", True)),
                require_price=bool(raw.get("require_price", True)),
                expected_currency=raw.get("expected_currency"),
            )
        )
    return cases


def _curl_json(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 240,
) -> tuple[int, str, dict[str, Any] | None]:
    command = [
        "curl",
        "-sS",
        "-m",
        str(timeout_seconds),
        "-X",
        method,
        "-w",
        "\n%{http_code}",
    ]
    for name, value in (headers or {}).items():
        command.extend(["-H", f"{name}: {value}"])
    if payload is not None:
        command.extend(["-H", "Content-Type: application/json", "-d", json.dumps(payload)])
    command.append(url)

    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    output = completed.stdout.rstrip("\n")
    if "\n" not in output:
        return 0, completed.stderr.strip() or output, None

    body, status_text = output.rsplit("\n", 1)
    try:
        status_code = int(status_text)
    except ValueError:
        status_code = 0

    try:
        parsed = json.loads(body) if body else None
    except json.JSONDecodeError:
        parsed = None

    error_text = completed.stderr.strip()
    if completed.returncode != 0 and error_text:
        body = f"{body}\n{error_text}".strip()
    return status_code, body, parsed


def _find_site_result(response: dict[str, Any], site: str) -> dict[str, Any] | None:
    for site_result in response.get("site_results", []):
        if site_result.get("site") == site:
            return site_result
    return None


def _validate_case(case: SmokeCase, response: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    site_result = _find_site_result(response, case.site)
    if site_result is None:
        return [f"Missing site_result for {case.site}."]

    status = str(site_result.get("status", ""))
    if status not in case.expected_statuses:
        errors.append(
            f"Unexpected status {status!r}; expected one of {list(case.expected_statuses)!r}."
        )

    parts = site_result.get("results", [])
    if not isinstance(parts, list):
        return [*errors, "site_result.results is not a list."]

    exact_parts = [
        part for part in parts
        if part.get("exact_match") is True
        and _normalize_sku(str(part.get("sku_found", ""))) == _normalize_sku(case.sku)
    ]
    if case.require_exact and not exact_parts:
        errors.append(f"No exact SKU result returned for {case.sku}.")

    priced_parts = [
        part for part in exact_parts
        if isinstance(part.get("price"), int | float) and float(part["price"]) > 0
    ]
    if case.require_price and not priced_parts:
        errors.append("No positive price returned for an exact result.")

    if case.expected_currency:
        currency_parts = priced_parts if case.require_price else exact_parts
        mismatched = [
            part.get("currency")
            for part in currency_parts
            if part.get("currency") != case.expected_currency
        ]
        if mismatched:
            errors.append(
                f"Currency mismatch; expected {case.expected_currency}, got {sorted(set(mismatched))}."
            )

    return errors


def _run_n8n_health(base_url: str, health_path: str, timeout_seconds: int) -> dict[str, Any]:
    status_code, body, parsed = _curl_json(
        url=base_url.rstrip("/") + health_path,
        timeout_seconds=timeout_seconds,
    )
    ok = 200 <= status_code < 300
    return {
        "id": "n8n-health",
        "url": base_url.rstrip("/") + health_path,
        "status_code": status_code,
        "ok": ok,
        "response": parsed if parsed is not None else body[:500],
        "errors": [] if ok else [f"N8N health returned HTTP {status_code}."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("docs/validation/latest_production_curl_smoke.json"))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.getenv("SCRAPER_SMOKE_TIMEOUT", "240")))
    args = parser.parse_args()

    api_base_url = os.getenv("API_BASE_URL", "").rstrip("/")
    api_key = os.getenv("API_KEY", "")
    if not api_base_url:
        print("API_BASE_URL is required.", file=sys.stderr)
        return 2
    if not api_key:
        print("API_KEY is required.", file=sys.stderr)
        return 2

    cases = _load_cases(args.manifest)
    results: list[dict[str, Any]] = []
    all_ok = True

    health_status, health_body, health_json = _curl_json(
        url=f"{api_base_url}/api/v1/health",
        timeout_seconds=args.timeout_seconds,
    )
    health_ok = 200 <= health_status < 300
    results.append(
        {
            "id": "scraper-api-health",
            "url": f"{api_base_url}/api/v1/health",
            "status_code": health_status,
            "ok": health_ok,
            "response": health_json if health_json is not None else health_body[:500],
            "errors": [] if health_ok else [f"API health returned HTTP {health_status}."],
        }
    )
    all_ok = all_ok and health_ok

    for case in cases:
        request_payload = {
            "sku": case.sku,
            "brand": case.brand,
            "sites": [case.site],
        }
        status_code, body, parsed = _curl_json(
            url=f"{api_base_url}/api/v1/lookup",
            method="POST",
            headers={"X-API-Key": api_key},
            payload=request_payload,
            timeout_seconds=args.timeout_seconds,
        )

        errors: list[str] = []
        if not (200 <= status_code < 300):
            errors.append(f"HTTP {status_code}: {body[:500]}")
        elif parsed is None:
            errors.append("Response was not valid JSON.")
        else:
            errors.extend(_validate_case(case, parsed))

        ok = not errors
        all_ok = all_ok and ok
        site_result = _find_site_result(parsed or {}, case.site) if parsed else None
        exact_count = 0
        priced_count = 0
        if site_result:
            exact_parts = [
                part for part in site_result.get("results", [])
                if part.get("exact_match") is True
            ]
            exact_count = len(exact_parts)
            priced_count = sum(
                1 for part in exact_parts
                if isinstance(part.get("price"), int | float) and float(part["price"]) > 0
            )

        results.append(
            {
                "id": case.id,
                "site": case.site,
                "sku": case.sku,
                "brand": case.brand,
                "status_code": status_code,
                "site_status": site_result.get("status") if site_result else None,
                "ok": ok,
                "exact_count": exact_count,
                "priced_count": priced_count,
                "errors": errors,
                "request": request_payload,
                "response": parsed,
            }
        )

    n8n_base_url = os.getenv("N8N_BASE_URL", "").rstrip("/")
    if n8n_base_url:
        n8n_result = _run_n8n_health(
            n8n_base_url,
            os.getenv("N8N_HEALTH_PATH", "/healthz"),
            args.timeout_seconds,
        )
        results.append(n8n_result)
        all_ok = all_ok and bool(n8n_result["ok"])

    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "api_base_url": api_base_url,
        "n8n_base_url": n8n_base_url or None,
        "success": all_ok,
        "cases": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
