import threading
from dataclasses import dataclass, field


@dataclass
class StatisticsSnapshot:
    messages_processed: int = 0
    messages_succeeded: int = 0
    messages_failed: int = 0
    total_retries: int = 0
    total_processing_time_ms: float = 0.0
    total_tokens_used: int = 0
    current_queue_length: int = 0
    idle_workers: int = 0
    active_workers: int = 0

    def to_api_dict(self) -> dict[str, int | float]:
        avg_time = (
            self.total_processing_time_ms / self.messages_processed
            if self.messages_processed
            else 0.0
        )
        avg_tokens = (
            self.total_tokens_used / self.messages_succeeded
            if self.messages_succeeded
            else 0.0
        )
        return {
            "messagesProcessed": self.messages_processed,
            "messagesSucceeded": self.messages_succeeded,
            "messagesFailed": self.messages_failed,
            "totalRetries": self.total_retries,
            "averageProcessingTimeMs": round(avg_time, 2),
            "averageTokensPerMessage": round(avg_tokens, 2),
            "totalTokensUsed": self.total_tokens_used,
            "currentQueueLength": self.current_queue_length,
            "idleWorkers": self.idle_workers,
            "activeWorkers": self.active_workers,
        }


@dataclass
class StatisticsCollector:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    messages_processed: int = 0
    messages_succeeded: int = 0
    messages_failed: int = 0
    total_retries: int = 0
    total_processing_time_ms: float = 0.0
    total_tokens_used: int = 0

    def record_success(
        self,
        *,
        processing_time_ms: float,
        tokens_used: int,
        retry_count: int,
    ) -> None:
        with self._lock:
            self.messages_processed += 1
            self.messages_succeeded += 1
            self.total_retries += retry_count
            self.total_processing_time_ms += processing_time_ms
            self.total_tokens_used += tokens_used

    def record_failure(self, *, retry_count: int) -> None:
        with self._lock:
            self.messages_processed += 1
            self.messages_failed += 1
            self.total_retries += retry_count

    def snapshot(
        self,
        *,
        queue_length: int,
        idle_workers: int,
        active_workers: int,
    ) -> StatisticsSnapshot:
        with self._lock:
            return StatisticsSnapshot(
                messages_processed=self.messages_processed,
                messages_succeeded=self.messages_succeeded,
                messages_failed=self.messages_failed,
                total_retries=self.total_retries,
                total_processing_time_ms=self.total_processing_time_ms,
                total_tokens_used=self.total_tokens_used,
                current_queue_length=queue_length,
                idle_workers=idle_workers,
                active_workers=active_workers,
            )
