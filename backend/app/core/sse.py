"""In-process SSE Hub with ping heartbeat."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any


class SSEHub:
    def __init__(self) -> None:
        self._subs: dict[int, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, customer_id: int) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subs[customer_id].add(queue)
        return queue

    async def unsubscribe(self, customer_id: int, queue: asyncio.Queue) -> None:
        async with self._lock:
            self._subs[customer_id].discard(queue)
            if not self._subs[customer_id]:
                del self._subs[customer_id]

    async def publish(self, customer_id: int, event: str, data: dict[str, Any]) -> None:
        payload = {"event": event, "data": data}
        async with self._lock:
            queues = list(self._subs.get(customer_id, set()))
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass


sse_hub = SSEHub()


def format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def event_stream(
    customer_id: int,
    *,
    ping_interval: float = 15.0,
) -> AsyncIterator[str]:
    queue = await sse_hub.subscribe(customer_id)
    try:
        yield format_sse("ping", {"ts": asyncio.get_event_loop().time()})
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=ping_interval)
                yield format_sse(item["event"], item["data"])
            except TimeoutError:
                yield format_sse("ping", {"ts": asyncio.get_event_loop().time()})
    finally:
        await sse_hub.unsubscribe(customer_id, queue)
