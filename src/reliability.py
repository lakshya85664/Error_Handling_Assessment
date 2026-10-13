
from collections import defaultdict
from threading import Lock
from time import monotonic
from typing import Any


class RateLimiter:
    """Process-local sliding-window rate limiter."""

    def __init__(self, limit: int = 5, window_seconds: float = 60.0):
        if limit < 1 or window_seconds <= 0:
            raise ValueError("Limit and window must be positive")

        self.limit = limit
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = monotonic()

        with self._lock:
            recent = [
                timestamp
                for timestamp in self._calls[key]
                if now - timestamp < self.window_seconds
            ]

            if len(recent) >= self.limit:
                self._calls[key] = recent
                return False

            recent.append(now)
            self._calls[key] = recent
            return True


class IdempotencyStore:
    """Thread-safe, process-local store for completed request results."""

    def __init__(self):
        self._results: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            result = self._results.get(request_id)
            return dict(result) if result is not None else None

    def put(self, request_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            self._results[request_id] = dict(result)
