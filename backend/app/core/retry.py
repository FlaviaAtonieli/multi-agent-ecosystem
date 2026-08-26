import time
from collections.abc import Callable


def retry_on_transient_error[T](
    func: Callable[[], T],
    *,
    exceptions: tuple[type[Exception], ...],
    attempts: int = 2,
    delay_seconds: float = 1.5,
) -> T:
    """Retries a real external call a bounded number of times on transient
    failures -- rate limits, network blips, or a free/shared model that
    occasionally ignores the requested response schema.

    Not a substitute for correctness: only the exception types passed in
    `exceptions` are retried, and the final attempt's exception always
    propagates if every attempt fails.
    """
    last_exc: Exception
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except exceptions as exc:
            last_exc = exc
            if attempt < attempts:
                time.sleep(delay_seconds)
    raise last_exc
