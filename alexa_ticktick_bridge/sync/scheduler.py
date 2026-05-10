from __future__ import annotations

import asyncio
import random

from alexa_ticktick_bridge.errors import RateLimited, RemoteServiceError
from alexa_ticktick_bridge.sync.service import SyncService


async def run_forever(
    service: SyncService,
    *,
    interval_seconds: int,
    jitter_seconds: int,
    max_backoff_seconds: int,
) -> None:
    backoff = interval_seconds
    while True:
        try:
            await service.sync_once()
            backoff = interval_seconds
        except (RateLimited, RemoteServiceError):
            backoff = min(max(backoff * 2, interval_seconds), max_backoff_seconds)
        sleep_for = backoff + random.uniform(0, jitter_seconds)
        await asyncio.sleep(sleep_for)
