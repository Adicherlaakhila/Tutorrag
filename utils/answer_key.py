"""Server-side quiz answer key loader (encrypted at rest)."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_ANSWERS_PATH = Path(__file__).resolve().parent.parent / "private" / "answers.enc"
# Server-only pepper used to protect the answer file at rest.
# Answers are not shipped as a public CSV.
_PEPPER = b"tutorrag-quiz-answers-v1-server-only"


def _fernet() -> Fernet:
    digest = hashlib.sha256(_PEPPER).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


@lru_cache(maxsize=1)
def load_answer_key() -> dict[str, dict[str, str]]:
    if not _ANSWERS_PATH.exists():
        logger.error("Encrypted answer key missing")
        return {}
    try:
        raw = _fernet().decrypt(_ANSWERS_PATH.read_bytes())
        data = json.loads(raw.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError, OSError):
        logger.exception("Failed to decrypt answer key")
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


# Eager alias used by quiz grading.
ANSWER_KEY: dict[str, dict[str, str]] = load_answer_key()
