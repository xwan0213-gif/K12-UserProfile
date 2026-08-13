"""进程内 SSE 发布/订阅中心（按 customer_id 广播），带 ping 心跳。"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any


class SSEHub:
    """内存订阅表：customer_id → 若干 Queue；多实例部署时不会跨进程共享。"""

    def __init__(self) -> None:
        self._subs: dict[int, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, customer_id: int) -> asyncio.Queue[dict[str, Any]]:
        """注册订阅队列（有界，防慢消费者撑爆内存）。"""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subs[customer_id].add(queue)
        return queue

    async def unsubscribe(self, customer_id: int, queue: asyncio.Queue) -> None:
        """取消订阅；该客户无订阅者时清理 key。"""
        async with self._lock:
            self._subs[customer_id].discard(queue)
            if not self._subs[customer_id]:
                del self._subs[customer_id]

    async def publish(self, customer_id: int, event: str, data: dict[str, Any]) -> None:
        """向该客户所有订阅者投递事件；队列满则丢弃该条。"""
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
    """编码为标准 SSE 文本帧。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def event_stream(
    customer_id: int,
    *,
    ping_interval: float = 15.0,
) -> AsyncIterator[str]:
    """
    长连接事件流：先发 ping，再阻塞读队列；超时补 ping 保活。
    连接断开时在 finally 中退订。
    """
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
