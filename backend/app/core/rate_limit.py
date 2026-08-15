from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = monotonic()
        threshold = now - window_seconds
        with self._lock:
            entries = self._requests[key]
            while entries and entries[0] <= threshold:
                entries.popleft()
            if len(entries) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Muitas tentativas. Aguarde alguns instantes e tente novamente.",
                    headers={"Retry-After": str(window_seconds)},
                )
            entries.append(now)


limiter = InMemoryRateLimiter()


def rate_limit(name: str, max_requests: int, window_seconds: int) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        limiter.check(f"{name}:{client_ip}", max_requests, window_seconds)

    return dependency


register_rate_limit = rate_limit("register", 3, 60)
login_rate_limit = rate_limit("login", 5, 60)
renew_rate_limit = rate_limit("renew", 10, 60)
