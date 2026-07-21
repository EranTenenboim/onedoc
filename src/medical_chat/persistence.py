import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from medical_chat.domain import ChatMessage
from medical_chat.models import MessageStatus


class SqlitePersistence:
    """SQLite-backed persistence for chat messages across restarts."""

    def __init__(self, db_path: str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        status TEXT NOT NULL,
                        answer TEXT,
                        error TEXT,
                        created_at TEXT NOT NULL,
                        completed_at TEXT,
                        processing_time_ms REAL,
                        tokens_used INTEGER NOT NULL DEFAULT 0,
                        retry_count INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id, created_at)
                    """
                )
                connection.commit()

    def load_all(self) -> list[ChatMessage]:
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM messages ORDER BY created_at ASC"
                ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def upsert(self, message: ChatMessage) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO messages (
                        message_id, conversation_id, question, status, answer, error,
                        created_at, completed_at, processing_time_ms, tokens_used, retry_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(message_id) DO UPDATE SET
                        conversation_id=excluded.conversation_id,
                        question=excluded.question,
                        status=excluded.status,
                        answer=excluded.answer,
                        error=excluded.error,
                        created_at=excluded.created_at,
                        completed_at=excluded.completed_at,
                        processing_time_ms=excluded.processing_time_ms,
                        tokens_used=excluded.tokens_used,
                        retry_count=excluded.retry_count
                    """,
                    (
                        message.message_id,
                        message.conversation_id,
                        message.question,
                        message.status.value,
                        message.answer,
                        message.error,
                        message.created_at.isoformat(),
                        message.completed_at.isoformat() if message.completed_at else None,
                        message.processing_time_ms,
                        message.tokens_used,
                        message.retry_count,
                    ),
                )
                connection.commit()

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> ChatMessage:
        completed_at = (
            datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
        )
        return ChatMessage(
            question=row["question"],
            message_id=row["message_id"],
            conversation_id=row["conversation_id"],
            status=MessageStatus(row["status"]),
            answer=row["answer"],
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=completed_at,
            processing_time_ms=row["processing_time_ms"],
            tokens_used=row["tokens_used"] or 0,
            retry_count=row["retry_count"] or 0,
        )
