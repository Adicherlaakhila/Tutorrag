"""Server-side rate limiting for paid LLM API calls."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitConfig:
    max_requests: int = 8
    window_seconds: int = 600  # 10 minutes
    global_max_requests: int = 80
    global_window_seconds: int = 600


class RateLimiter:
    """Thread-safe sliding-window limiter for Groq (or other paid) calls."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._events: dict[str, list[float]] = defaultdict(list)
        self._global: list[float] = []
        self._lock = threading.Lock()

    def _prune(self, events: list[float], window: int, now: float) -> list[float]:
        cutoff = now - window
        return [ts for ts in events if ts >= cutoff]

    def allow(self, client_key: str) -> tuple[bool, str | None]:
        """Return (allowed, error_message)."""
        key = (client_key or "anonymous").strip() or "anonymous"
        now = time.time()
        with self._lock:
            self._events[key] = self._prune(
                self._events[key], self.config.window_seconds, now
            )
            self._global = self._prune(
                self._global, self.config.global_window_seconds, now
            )

            if len(self._global) >= self.config.global_max_requests:
                return False, (
                    "TutorRAG is receiving many requests right now. "
                    "Please wait a few minutes and try again."
                )

            if len(self._events[key]) >= self.config.max_requests:
                minutes = max(1, self.config.window_seconds // 60)
                return False, (
                    f"You have reached the tutoring request limit "
                    f"({self.config.max_requests} per {minutes} minutes). "
                    "Please wait and try again."
                )

            self._events[key].append(now)
            self._global.append(now)
            return True, None


# Process-wide limiter shared by Streamlit sessions on one server.
GROQ_RATE_LIMITER = RateLimiter()
