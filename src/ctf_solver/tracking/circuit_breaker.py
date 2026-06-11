"""Per-provider circuit breaker — stops dispatching after N consecutive failures."""

from __future__ import annotations

import time


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._consecutive_failures = 0
        self._last_failure_time: float | None = None

    def record_success(self) -> None:
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        self._last_failure_time = time.monotonic()

    def is_available(self) -> bool:
        if self._consecutive_failures < self.failure_threshold:
            return True
        if self._last_failure_time is None:
            return True
        if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
            self._consecutive_failures = 0
            return True
        return False
