"""Background interview demo runner (formerly exposed via FastAPI).

Use ``make interview-demo`` or invoke ``scripts/interview_scraper_demo.py`` directly.
Remote automation should shell out to those entry points instead of HTTP routes.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.models.schemas import InterviewDemoRequest, InterviewDemoStatusResponse

_interview_demo_runs: dict[str, InterviewDemoStatusResponse] = {}
_interview_demo_tasks: set[asyncio.Task[None]] = set()


def _summarize_interview_demo(output_path: Path) -> str:
    if not output_path.exists():
        return "Demo terminou, mas o arquivo de resultado nao foi encontrado."

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    total = len(cases)
    success = sum(1 for case in cases if case.get("status") == "success")
    lines = [
        "Demo interview finalizado",
        f"Sites visitados: {total}",
        f"Com preco claro: {success}",
        "",
        "Resumo:",
    ]
    for case in cases:
        site = str(case.get("site") or case.get("case_id") or "site").upper()
        sku = case.get("sku") or "-"
        status = case.get("status") or "unknown"
        best = case.get("best_price") or {}
        price = best.get("price")
        currency = best.get("currency") or "BRL"
        if price:
            lines.append(f"- {site} {sku}: {currency} {float(price):.2f}")
        else:
            lines.append(f"- {site} {sku}: {status}")
    return "\n".join(lines)[:3900]


async def _run_interview_demo(demo_id: str, request: InterviewDemoRequest) -> None:
    run = _interview_demo_runs[demo_id]
    output_path = Path(run.output_path)
    env = os.environ.copy()
    env["PLAYWRIGHT_HEADLESS"] = "true" if request.headless else "false"
    env.setdefault("UV_CACHE_DIR", "/tmp/uv-cache")

    command = [
        "uv",
        "run",
        "--extra",
        "dev",
        "python",
        "scripts/interview_scraper_demo.py",
        "--sites",
        request.sites,
        "--timeout-seconds",
        str(request.timeout_seconds),
        "--json-out",
        str(output_path),
    ]
    if request.headless:
        command.append("--headless")

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        run.completed_at = datetime.now(UTC)
        run.return_code = process.returncode
        if process.returncode == 0:
            run.status = "completed"
            run.summary_text = _summarize_interview_demo(output_path)
        else:
            run.status = "failed"
            error = (stderr or stdout).decode("utf-8", errors="replace").strip()
            run.error_message = error[-1500:] or f"Demo failed with code {process.returncode}"
    except Exception as exc:
        run.status = "failed"
        run.completed_at = datetime.now(UTC)
        run.error_message = str(exc)


async def start_interview_demo(request: InterviewDemoRequest) -> InterviewDemoStatusResponse:
    """Start the local headed interview demo in the background."""
    demo_id = str(uuid4())
    output_path = Path("docs/validation") / f"interview_demo_{demo_id}.json"
    run = InterviewDemoStatusResponse(
        demo_id=demo_id,
        status="running",
        telegram_chat_id=request.chat_id,
        started_at=datetime.now(UTC),
        sites=request.sites,
        output_path=str(output_path),
    )
    _interview_demo_runs[demo_id] = run
    task = asyncio.create_task(_run_interview_demo(demo_id, request))
    _interview_demo_tasks.add(task)
    task.add_done_callback(_interview_demo_tasks.discard)
    return run


def get_interview_demo_status(demo_id: str) -> InterviewDemoStatusResponse | None:
    """Return in-memory status for a background demo run, if present."""
    return _interview_demo_runs.get(demo_id)
