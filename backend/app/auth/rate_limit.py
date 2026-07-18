from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from app.core.errors import AppError


class RegistrationRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, source: str) -> None:
        now = monotonic()
        with self._lock:
            attempts = self._attempts[source]
            while attempts and attempts[0] <= now - self.window_seconds:
                attempts.popleft()
            if len(attempts) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - attempts[0])))
                raise AppError(
                    429,
                    "registration_rate_limited",
                    "注册尝试过于频繁，请稍后再试",
                    headers={"Retry-After": str(retry_after)},
                )
            attempts.append(now)
