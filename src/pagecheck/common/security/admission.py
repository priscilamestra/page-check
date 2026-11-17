"""Process-local admission control for a single-worker private audit API.

Limits are GLOBAL, not per-user identities. This is one defense layer; it is not
an internet-facing abuse shield or distributed quota. Use one API worker only.
"""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Iterator


class AuditAdmissionError(RuntimeError):
    """A scan was rejected without launching network or browser work."""


class AuditAdmission:
    def __init__(self, *, max_concurrent: int = 1, max_per_minute: int = 6,
                 clock=monotonic) -> None:
        if not 1 <= max_concurrent <= 4 or not 1 <= max_per_minute <= 60:
            raise ValueError("Invalid audit admission limits")
        self._slots = BoundedSemaphore(max_concurrent)
        self._lock = Lock()
        self._timestamps: deque[float] = deque()
        self._max_per_minute = max_per_minute
        self._clock = clock

    @contextmanager
    def enter(self) -> Iterator[None]:
        # Never queue scans: excess traffic immediately gets HTTP 429.
        if not self._slots.acquire(blocking=False):
            raise AuditAdmissionError("Audit capacity reached. Try again later.")
        try:
            with self._lock:
                now = self._clock()
                while self._timestamps and now - self._timestamps[0] >= 60:
                    self._timestamps.popleft()
                if len(self._timestamps) >= self._max_per_minute:
                    raise AuditAdmissionError("Audit rate limit reached. Try again later.")
                self._timestamps.append(now)
            yield
        finally:
            self._slots.release()


# The Render Blueprint intentionally runs ONE Uvicorn worker. A multi-instance
# rollout requires an external shared rate limiter, not this in-memory object.
production_audit_admission = AuditAdmission()
