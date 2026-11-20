"""Load the quiz answer key from host secrets only (never from shipped files)."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Local-only fallback path. Must remain gitignored and must never be committed.
_DEV_ANSWERS_PATH = (
    Path(__file__).resolve().parent.parent / "private" / "answers.dev.json"
)


def _from_mapping(data: Any) -> dict[str, dict[str, str]]:
    if not isinstance(data, dict):
        return {}
    cleaned: dict[str, dict[str, str]] = {}
    for qid, payload in data.items():
        if not isinstance(payload, dict):
            continue
        correct = str(payload.get("correct_answer", "")).strip().upper()
        explanation = str(payload.get("explanation", "")).strip()
        if correct in {"A", "B", "C", "D"}:
            cleaned[str(qid)] = {
                "correct_answer": correct,
                "explanation": explanation,
            }
    return cleaned


def _read_secret_json() -> dict[str, dict[str, str]] | None:
    raw = os.getenv("QUIZ_ANSWER_BANK", "").strip()
    if not raw:
        try:
            import streamlit as st

            secrets = getattr(st, "secrets", None)
            if secrets is not None and "QUIZ_ANSWER_BANK" in secrets:
                value = secrets["QUIZ_ANSWER_BANK"]
                if isinstance(value, dict):
                    return _from_mapping(value)
                raw = str(value).strip()
        except Exception:
            raw = ""
    if not raw:
        return None
    try:
        return _from_mapping(json.loads(raw))
    except json.JSONDecodeError:
        logger.exception("QUIZ_ANSWER_BANK is not valid JSON")
        return {}


def _read_dev_file() -> dict[str, dict[str, str]] | None:
    """Optional local developer file; never used as a shipped publish artifact."""
    if os.getenv("TUTORRAG_DISABLE_DEV_ANSWERS", "").strip() == "1":
        return None
    if not _DEV_ANSWERS_PATH.exists():
        return None
    try:
        return _from_mapping(json.loads(_DEV_ANSWERS_PATH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed reading local developer answer file")
        return {}


@lru_cache(maxsize=1)
def load_answer_key() -> dict[str, dict[str, str]]:
    """
    Resolve answers in this order:
    1) QUIZ_ANSWER_BANK host secret / env (production)
    2) gitignored private/answers.dev.json (local development only)
    """
    secret_data = _read_secret_json()
    if secret_data is not None:
        return secret_data
    dev_data = _read_dev_file()
    if dev_data is not None:
        return dev_data
    logger.warning("Quiz answer key unavailable (set QUIZ_ANSWER_BANK secret)")
    return {}


def get_answer_key() -> dict[str, dict[str, str]]:
    """Return the current answer key (clears easily in tests via cache_clear)."""
    return load_answer_key()


def clear_answer_key_cache() -> None:
    load_answer_key.cache_clear()


class _AnswerKeyProxy(dict):
    """Dict-like proxy so imports of ANSWER_KEY always see the current secret."""

    def _data(self) -> dict[str, dict[str, str]]:
        return get_answer_key()

    def __getitem__(self, key):  # type: ignore[override]
        return self._data()[key]

    def get(self, key, default=None):  # type: ignore[override]
        return self._data().get(key, default)

    def keys(self):  # type: ignore[override]
        return self._data().keys()

    def __contains__(self, key):  # type: ignore[override]
        return key in self._data()

    def __len__(self):  # type: ignore[override]
        return len(self._data())

    def items(self):  # type: ignore[override]
        return self._data().items()


ANSWER_KEY = _AnswerKeyProxy()
