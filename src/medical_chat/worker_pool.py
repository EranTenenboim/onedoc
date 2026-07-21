import asyncio
import time
from datetime import UTC, datetime
from uuid import uuid4

from medical_chat.config import Settings
from medical_chat.domain import InteractionLogEntry
from medical_chat.llm.base import BaseLLMClient, LLMResult
from medical_chat.models import MessageStatus
from medical_chat.statistics import StatisticsCollector
from medical_chat.storage import MessageQueue, MessageStore, SharedLog
from medical_chat.stream_hub import StreamEvent, StreamHub


class WorkerPool:
    """On-demand worker pool capped at CPU core count with idle shutdown."""

    def __init__(
        self,
        *,
        settings: Settings,
        store: MessageStore,
        queue: MessageQueue,
        shared_log: SharedLog,
        llm_client: BaseLLMClient,
        stats: StatisticsCollector,
        stream_hub: StreamHub,
    ) -> None:
        self._settings = settings
        self._store = store
        self._queue = queue
        self._shared_log = shared_log
        self._llm_client = llm_client
        self._stats = stats
        self._stream_hub = stream_hub
        self._workers: dict[str, asyncio.Task[None]] = {}
        self._idle_workers: set[str] = set()
        self._active_workers: set[str] = set()
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._dispatcher(), name="worker-dispatcher")

    async def stop(self) -> None:
        self._running = False
        async with self._lock:
            tasks = list(self._workers.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatcher(self) -> None:
        while self._running:
            message_id = await self._queue.dequeue()
            worker_id = await self._acquire_worker()
            asyncio.create_task(
                self._process_message(worker_id, message_id),
                name=f"worker-{worker_id}-job",
            )

    async def _acquire_worker(self) -> str:
        async with self._lock:
            if self._idle_workers:
                worker_id = self._idle_workers.pop()
                self._active_workers.add(worker_id)
                return worker_id
            if len(self._workers) < self._settings.max_workers:
                worker_id = str(uuid4())[:8]
                task = asyncio.create_task(
                    self._worker_loop(worker_id),
                    name=f"worker-{worker_id}",
                )
                self._workers[worker_id] = task
                self._active_workers.add(worker_id)
                return worker_id
        while self._running:
            await asyncio.sleep(0.05)
            async with self._lock:
                if self._idle_workers:
                    worker_id = self._idle_workers.pop()
                    self._active_workers.add(worker_id)
                    return worker_id
        raise RuntimeError("Worker pool is shutting down")

    async def _worker_loop(self, worker_id: str) -> None:
        try:
            while self._running:
                await asyncio.sleep(self._settings.worker_idle_timeout)
                async with self._lock:
                    if worker_id in self._idle_workers:
                        self._idle_workers.discard(worker_id)
                        self._workers.pop(worker_id, None)
                        return
        except asyncio.CancelledError:
            return

    async def _process_message(self, worker_id: str, message_id: str) -> None:
        message = self._store.get(message_id)
        if message is None:
            self._queue.task_done()
            await self._release_worker(worker_id)
            return

        message.status = MessageStatus.PROCESSING
        self._store.update(message)

        history = self._store.conversation_history(
            message.conversation_id,
            before_message_id=message.message_id,
            max_turns=20,
        )

        started = time.perf_counter()
        retry_count = 0
        last_error: str | None = None
        result: LLMResult | None = None

        while retry_count <= self._settings.max_retries:
            try:
                chunks: list[str] = []
                async for chunk in self._llm_client.stream(message.question, history):
                    chunks.append(chunk)
                    await self._stream_hub.publish(
                        message_id,
                        StreamEvent(event="token", data=chunk),
                    )
                answer = "".join(chunks)
                tokens = len(message.question.split()) + len(answer.split())
                if history:
                    tokens += sum(len(turn.content.split()) for turn in history)
                result = LLMResult(answer=answer, tokens_used=tokens)
                break
            except Exception as exc:  # noqa: BLE001 - retry boundary
                last_error = str(exc)
                retry_count += 1
                if retry_count <= self._settings.max_retries:
                    await asyncio.sleep(self._settings.retry_delay)

        elapsed_ms = (time.perf_counter() - started) * 1000
        message.retry_count = max(0, retry_count - 1)
        message.completed_at = datetime.now(UTC)
        message.processing_time_ms = elapsed_ms

        if result is not None:
            message.status = MessageStatus.COMPLETED
            message.answer = result.answer
            message.tokens_used = result.tokens_used
            self._stats.record_success(
                processing_time_ms=elapsed_ms,
                tokens_used=result.tokens_used,
                retry_count=message.retry_count,
            )
            self._shared_log.append(
                InteractionLogEntry(
                    timestamp=message.completed_at,
                    worker_id=worker_id,
                    message_id=message.message_id,
                    question=message.question,
                    response=result.answer,
                    error=None,
                )
            )
            await self._stream_hub.publish(
                message_id,
                StreamEvent(event="done", data=result.answer),
            )
        else:
            message.status = MessageStatus.FAILED
            message.error = last_error or "LLM request failed after retries"
            self._stats.record_failure(retry_count=message.retry_count)
            self._shared_log.append(
                InteractionLogEntry(
                    timestamp=message.completed_at,
                    worker_id=worker_id,
                    message_id=message.message_id,
                    question=message.question,
                    response=None,
                    error=message.error,
                )
            )
            await self._stream_hub.publish(
                message_id,
                StreamEvent(event="error", data=message.error),
            )

        self._store.update(message)
        await self._stream_hub.close(message_id)
        self._queue.task_done()
        await self._release_worker(worker_id)

    async def _release_worker(self, worker_id: str) -> None:
        async with self._lock:
            self._active_workers.discard(worker_id)
            if worker_id in self._workers:
                self._idle_workers.add(worker_id)

    def worker_counts(self) -> tuple[int, int]:
        return len(self._idle_workers), len(self._active_workers)
