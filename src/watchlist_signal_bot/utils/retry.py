from __future__ import annotations

import time
from collections.abc import Callable


def retry_call[T](
    func: Callable[[], T],
    *,
    attempts: int = 2,
    delay_seconds: float = 1.5,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error
