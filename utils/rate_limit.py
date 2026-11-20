"""Server-side rate limiting for paid LLM API calls (IP + session + budgets)."""

from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict
from dataclasses import dataclass

from utils.usage_budget import GROQ_USAGE_BUDGET


@dataclass(frozen=True)
class RateLimitConfig:
    per_ip_max_requests: int = 8
    per_ip_window_seconds: int = 600
    per_session_max_requests: int = 4
    per_session_window_seconds: int = 600
    min_interval_seconds: float = 10.0
    global_max_requests: int = 30
    global_window_seconds: int = 600


class RateLimiter:
    """Thread-safe sliding-window limiter keyed by IP/fingerprint and session."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._by_ip: dict[str, list[float]] = defaultdict(list)
        self._by_session: dict[str, list[float]] = defaultdict(list)
        self._last_by_ip: dict[str, float] = {}
        self._global: list[float] = []
        self._lock = threading.Lock()

    def _prune(self, events: list[float], window: int, now: float) -> list[float]:
        cutoff = now - window
        return [ts for ts in events if ts >= cutoff]

    def allow(
        self,
        *,
        ip_key: str,
        session_key: str,
        enforce_budget: bool = True,
    ) -> tuple[bool, str | None]:
        """Return (allowed, error_message)."""
        ip = (ip_key or "unknown-ip").strip() or "unknown-ip"
        session = (session_key or "anonymous").strip() or "anonymous"
        now = time.time()

        if enforce_budget:
            ok_budget, budget_msg = GROQ_USAGE_BUDGET.allow_and_increment(ip)
            if not ok_budget:
                return False, budget_msg

        with self._lock:
            self._by_ip[ip] = self._prune(
                self._by_ip[ip], self.config.per_ip_window_seconds, now
            )
            self._by_session[session] = self._prune(
                self._by_session[session],
                self.config.per_session_window_seconds,
                now,
            )
            self._global = self._prune(
                self._global, self.config.global_window_seconds, now
            )

            if len(self._global) >= self.config.global_max_requests:
                return False, (
                    "TutorRAG is receiving many requests right now. "
                    "Please wait a few minutes and try again."
                )

            last = self._last_by_ip.get(ip)
            if last is not None and (now - last) < self.config.min_interval_seconds:
                wait_for = int(self.config.min_interval_seconds - (now - last)) + 1
                return False, (
                    f"Please wait about {wait_for} seconds before sending another "
                    "AI tutoring request."
                )

            if len(self._by_ip[ip]) >= self.config.per_ip_max_requests:
                minutes = max(1, self.config.per_ip_window_seconds // 60)
                return False, (
                    f"This network has reached the tutoring request limit "
                    f"({self.config.per_ip_max_requests} per {minutes} minutes). "
                    "Please wait and try again."
                )

            if len(self._by_session[session]) >= self.config.per_session_max_requests:
                minutes = max(1, self.config.per_session_window_seconds // 60)
                return False, (
                    f"You have reached the session tutoring limit "
                    f"({self.config.per_session_max_requests} per {minutes} minutes). "
                    "Please wait and try again."
                )

            self._by_ip[ip].append(now)
            self._by_session[session].append(now)
            self._global.append(now)
            self._last_by_ip[ip] = now
            return True, None


def fingerprint_client(ip: str, user_agent: str = "") -> str:
    material = f"{ip}|{user_agent}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:32]


GROQ_RATE_LIMITER = RateLimiter()


# Separate limiter for quiz generation to reduce answer-bank scraping.
class QuizRateLimiter(RateLimiter):
    def __init__(self) -> None:
        super().__init__(
            RateLimitConfig(
                per_ip_max_requests=3,
                per_ip_window_seconds=86400,  # 3 quizzes / day / IP
                per_session_max_requests=2,
                per_session_window_seconds=86400,
                min_interval_seconds=20.0,
                global_max_requests=80,
                global_window_seconds=86400,
            )
        )

    def allow(self, *, ip_key: str, session_key: str, enforce_budget: bool = False):
        return super().allow(
            ip_key=ip_key,
            session_key=session_key,
            enforce_budget=False,
        )


QUIZ_RATE_LIMITER = QuizRateLimiter()
