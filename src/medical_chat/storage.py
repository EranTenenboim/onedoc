import asyncio
import threading
from pathlib import Path
from uuid import uuid4

from medical_chat.domain import ChatMessage, ChatTurn, InteractionLogEntry
from medical_chat.models import MessageStatus
from medical_chat.persistence import SqlitePersistence


class MessageStore:
    """Thread-safe message store with optional SQLite persistence."""

    def __init__(self, persistence: SqlitePersistence | None = None) -> None:
        self._messages: dict[str, ChatMessage] = {}
        self._conversation_order: dict[str, list[str]] = {}
        self._lock = threading.Lock()
        self._persistence = persistence
        if persistence is not None:
            for message in persistence.load_all():
                self._messages[message.message_id] = message
                order = self._conversation_order.setdefault(message.conversation_id, [])
                order.append(message.message_id)

    def create(
        self,
        question: str,
        *,
        conversation_id: str | None = None,
    ) -> ChatMessage:
        conversation_id = conversation_id or str(uuid4())
        message = ChatMessage(question=question, conversation_id=conversation_id)
        with self._lock:
            self._messages[message.message_id] = message
            self._conversation_order.setdefault(conversation_id, []).append(
                message.message_id
            )
        if self._persistence is not None:
            self._persistence.upsert(message)
        return message

    def get(self, message_id: str) -> ChatMessage | None:
        with self._lock:
            return self._messages.get(message_id)

    def update(self, message: ChatMessage) -> None:
        with self._lock:
            self._messages[message.message_id] = message
        if self._persistence is not None:
            self._persistence.upsert(message)

    def conversation_history(
        self,
        conversation_id: str,
        *,
        before_message_id: str | None = None,
    ) -> list[ChatTurn]:
        """Return prior completed Q&A turns for agent-mode context."""
        with self._lock:
            message_ids = list(self._conversation_order.get(conversation_id, []))
            turns: list[ChatTurn] = []
            for message_id in message_ids:
                if before_message_id is not None and message_id == before_message_id:
                    break
                message = self._messages.get(message_id)
                if message is None or message.status != MessageStatus.COMPLETED:
                    continue
                if not message.answer:
                    continue
                turns.append(ChatTurn(role="user", content=message.question))
                turns.append(ChatTurn(role="assistant", content=message.answer))
            return turns


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
