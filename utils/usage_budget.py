"""Persistent daily/monthly Groq usage budgets (file-backed, server-side)."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _usage_path() -> Path:
    configured = os.getenv("TUTORRAG_USAGE_PATH", "").strip()
    if configured:
        return Path(configured)
    # Prefer a writable local data dir that is gitignored.
    root = Path(__file__).resolve().parent.parent / "data" / ".usage"
    root.mkdir(parents=True, exist_ok=True)
    return root / "groq_usage.json"


@dataclass(frozen=True)
class BudgetConfig:
    daily_limit: int = 40
    monthly_limit: int = 400


class UsageBudget:
    """Thread-safe persistent counters for paid LLM calls."""

    def __init__(self, config: BudgetConfig | None = None) -> None:
        self.config = config or BudgetConfig(
            daily_limit=int(os.getenv("GROQ_DAILY_LIMIT", "40")),
            monthly_limit=int(os.getenv("GROQ_MONTHLY_LIMIT", "400")),
        )
        self._lock = threading.Lock()
        self._path = _usage_path()

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"days": {}, "months": {}}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"days": {}, "months": {}}

    def _save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def allow_and_increment(self, ip_key: str) -> tuple[bool, str | None]:
        ip = (ip_key or "unknown-ip").strip() or "unknown-ip"
        now = self._utc_now()
        day = now.strftime("%Y-%m-%d")
        month = now.strftime("%Y-%m")
        with self._lock:
            data = self._load()
            days: dict[str, Any] = data.setdefault("days", {})
            months: dict[str, Any] = data.setdefault("months", {})
            day_bucket: dict[str, int] = days.setdefault(day, {})
            month_bucket: dict[str, int] = months.setdefault(month, {})

            # Global daily/monthly across all clients.
            global_day = int(day_bucket.get("_global", 0))
            global_month = int(month_bucket.get("_global", 0))
            if global_day >= self.config.daily_limit:
                return False, (
                    "TutorRAG has reached today's AI tutoring budget. "
                    "Please try again tomorrow."
                )
            if global_month >= self.config.monthly_limit:
                return False, (
                    "TutorRAG has reached this month's AI tutoring budget. "
                    "Please try again next month."
                )

            # Per-IP share of the budget (harder to monopolize).
            per_ip_daily = max(3, self.config.daily_limit // 4)
            per_ip_monthly = max(20, self.config.monthly_limit // 4)
            if int(day_bucket.get(ip, 0)) >= per_ip_daily:
                return False, (
                    "This network has reached today's AI tutoring limit. "
                    "Please try again tomorrow."
                )
            if int(month_bucket.get(ip, 0)) >= per_ip_monthly:
                return False, (
                    "This network has reached this month's AI tutoring limit. "
                    "Please try again next month."
                )

            day_bucket[ip] = int(day_bucket.get(ip, 0)) + 1
            month_bucket[ip] = int(month_bucket.get(ip, 0)) + 1
            day_bucket["_global"] = global_day + 1
            month_bucket["_global"] = global_month + 1
            # Light pruning of old day keys.
            for key in list(days.keys()):
                if key < (now.replace(day=1).strftime("%Y-%m-%d")) and key != day:
                    # keep current month days; drop older than ~40 days
                    try:
                        age = (now - datetime.strptime(key, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
                        if age > 40:
                            days.pop(key, None)
                    except ValueError:
                        days.pop(key, None)
            data["updated_at"] = int(time.time())
            self._save(data)
            return True, None


GROQ_USAGE_BUDGET = UsageBudget()
