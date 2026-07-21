from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from medical_chat.models import MessageStatus


@dataclass
class ChatMessage:
    question: str
    message_id: str = field(default_factory=lambda: str(uuid4()))
    status: MessageStatus = MessageStatus.PENDING
    answer: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    processing_time_ms: float | None = None
    tokens_used: int = 0
    retry_count: int = 0


@dataclass
class InteractionLogEntry:
    timestamp: datetime
    worker_id: str
    message_id: str
    question: str
    response: str | None
    error: str | None

    def to_json_line(self) -> str:
        import json

        return json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "workerId": self.worker_id,
                "messageId": self.message_id,
                "question": self.question,
                "response": self.response,
                "error": self.error,
            }
        )
