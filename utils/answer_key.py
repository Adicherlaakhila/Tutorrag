"""Load the quiz answer key from host secrets only (never from shipped files)."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.secrets_util import get_secret, get_secret_any

logger = logging.getLogger(__name__)

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
    raw_any = get_secret_any("QUIZ_ANSWER_BANK")
    if raw_any is None:
        return None
    if isinstance(raw_any, dict):
        return _from_mapping(raw_any)
    raw = str(raw_any).strip()
    if not raw:
        return None
    try:
        return _from_mapping(json.loads(raw))
    except json.JSONDecodeError:
        logger.exception("QUIZ_ANSWER_BANK is not valid JSON")
        return {}


def _read_dev_file() -> dict[str, dict[str, str]] | None:
    """Local developer file only when explicitly enabled."""
    if get_secret("TUTORRAG_ALLOW_DEV_ANSWERS") != "1":
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
    secret_data = _read_secret_json()
    if secret_data is not None:
        return secret_data
    dev_data = _read_dev_file()
    if dev_data is not None:
        return dev_data
    logger.warning("Quiz answer key unavailable (set QUIZ_ANSWER_BANK secret)")
    return {}


def get_answer_key() -> dict[str, dict[str, str]]:
    return load_answer_key()


def clear_answer_key_cache() -> None:
    load_answer_key.cache_clear()


class _AnswerKeyProxy(dict):
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
