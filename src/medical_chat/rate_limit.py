import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Thread-safe sliding-window rate limiter keyed by client identifier."""

    def __init__(self, *, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._max_requests > 0 and self._window_seconds > 0

    def allow(self, key: str) -> bool:
        if not self.enabled:
            return True

        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True

    def retry_after_seconds(self, key: str) -> int:
        if not self.enabled:
            return 0

        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            bucket = self._events.get(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                return 0
            return max(1, int(self._window_seconds - (now - bucket[0]) + 1))
