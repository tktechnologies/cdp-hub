#!/usr/bin/env python3
"""Drain Muvstok Redis job stream and show queue stats."""
from __future__ import annotations

import asyncio
import os
import sys

from redis.asyncio import Redis


async def main() -> int:
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        print("Set REDIS_URL", file=sys.stderr)
        return 1

    stream = os.environ.get("REDIS_JOB_STREAM", "muvstok:jobs")
    group = os.environ.get("REDIS_JOB_CONSUMER_GROUP", "muvstok-workers")
    dlq = os.environ.get("REDIS_DEAD_LETTER_STREAM", "muvstok:jobs:dead-letter")

    redis = Redis.from_url(url, decode_responses=True)
    try:
        for name in (stream, dlq):
            length = await redis.xlen(name)
            print(f"{name} XLEN={length}")
            try:
                pending = await redis.xpending(name, group)
                print(f"  XPENDING={pending}")
            except Exception as exc:
                print(f"  XPENDING error: {exc}")

        deleted = await redis.delete(stream)
        print(f"Deleted stream key {stream}: {deleted}")
        return 0
    finally:
        await redis.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
