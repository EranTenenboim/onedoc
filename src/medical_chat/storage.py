import asyncio
import threading
from pathlib import Path

from medical_chat.domain import ChatMessage, InteractionLogEntry


class MessageStore:
    """Thread-safe in-memory message store."""

    def __init__(self) -> None:
        self._messages: dict[str, ChatMessage] = {}
        self._lock = threading.Lock()

    def create(self, question: str) -> ChatMessage:
        message = ChatMessage(question=question)
        with self._lock:
            self._messages[message.message_id] = message
        return message

    def get(self, message_id: str) -> ChatMessage | None:
        with self._lock:
            return self._messages.get(message_id)

    def update(self, message: ChatMessage) -> None:
        with self._lock:
            self._messages[message.message_id] = message


class SharedLog:
    """Append-only shared log with safe concurrent writes."""

    def __init__(self, log_file: str) -> None:
        self._path = Path(log_file)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, entry: InteractionLogEntry) -> None:
        line = entry.to_json_line() + "\n"
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line)


class MessageQueue:
    """Async queue for pending chat messages."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    async def enqueue(self, message_id: str) -> None:
        await self._queue.put(message_id)

    async def dequeue(self) -> str:
        return await self._queue.get()

    def qsize(self) -> int:
        return self._queue.qsize()

    def task_done(self) -> None:
        self._queue.task_done()
