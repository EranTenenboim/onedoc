import asyncio
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamEvent:
    event: str
    data: str


class StreamHub:
    """Fan-out token/done/error events to SSE subscribers per message."""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[StreamEvent | None]]] = defaultdict(list)
        self._finished: dict[str, StreamEvent] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, message_id: str) -> asyncio.Queue[StreamEvent | None]:
        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        async with self._lock:
            finished = self._finished.get(message_id)
            self._queues[message_id].append(queue)
        if finished is not None:
            await queue.put(finished)
            await queue.put(None)
        return queue

    async def publish(self, message_id: str, event: StreamEvent) -> None:
        async with self._lock:
            if event.event in {"done", "error"}:
                self._finished[message_id] = event
            subscribers = list(self._queues.get(message_id, []))
        for queue in subscribers:
            await queue.put(event)

    async def close(self, message_id: str) -> None:
        async with self._lock:
            subscribers = list(self._queues.pop(message_id, []))
        for queue in subscribers:
            await queue.put(None)
