"""
Minimal in-process circuit breaker.

Used by services/meme_ai.py to stop hammering Gemini once it's clearly
failing, and fall back to Anthropic instead of retrying the dead provider
on every single request.

Deliberately process-local (not Redis-backed): the goal is just to stop a
single worker process from wasting 20-second timeouts on a provider that's
already down, not to perfectly synchronize breaker state across every
replica. A few extra requests retrying Gemini during the propagation window
across replicas is an acceptable tradeoff against the complexity of a
distributed breaker for this workload.
"""
from __future__ import annotations

import asyncio
import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"        # normal operation
    OPEN = "open"             # failing — short-circuit, skip straight to fallback
    HALF_OPEN = "half_open"   # recovery probe — allow exactly one trial request


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def allow_request(self) -> bool:
        """Whether a request should even be attempted against the
        protected provider right now."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self.recovery_timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    return True
                return False
            return True

    async def record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED

    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._state == CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
