"""Security-focused tests for rate limits, validation, and answer-key isolation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.answer_key import clear_answer_key_cache, get_answer_key
from utils.rate_limit import RateLimitConfig, RateLimiter
from utils.validation import validate_chat_question


def test_public_questions_csv_has_no_answers():
    text = (ROOT / "data" / "questions.csv").read_text(encoding="utf-8")
    header = text.splitlines()[0].lower()
    assert "correct_answer" not in header
    assert "explanation" not in header


def test_no_shipped_answer_ciphertext_or_pepper():
    assert not (ROOT / "private" / "answers.enc").exists()
    answer_key_source = (ROOT / "utils" / "answer_key.py").read_text(encoding="utf-8")
    assert "tutorrag-quiz-answers-v1-server-only" not in answer_key_source
    assert "Fernet" not in answer_key_source
    assert "_PEPPER" not in answer_key_source


def test_answer_key_loads_from_env_secret(monkeypatch):
    payload = {
        "QX1": {"correct_answer": "B", "explanation": "Because B"},
    }
    monkeypatch.setenv("QUIZ_ANSWER_BANK", json.dumps(payload))
    monkeypatch.setenv("TUTORRAG_DISABLE_DEV_ANSWERS", "1")
    clear_answer_key_cache()
    key = get_answer_key()
    assert key["QX1"]["correct_answer"] == "B"
    clear_answer_key_cache()


def test_answer_key_empty_without_secret_or_dev(monkeypatch, tmp_path):
    monkeypatch.delenv("QUIZ_ANSWER_BANK", raising=False)
    monkeypatch.setenv("TUTORRAG_DISABLE_DEV_ANSWERS", "1")
    clear_answer_key_cache()
    assert get_answer_key() == {}
    clear_answer_key_cache()


def test_chat_validation_blocks_abuse_inputs():
    assert validate_chat_question("")[0] is False
    assert validate_chat_question("ok")[0] is False
    assert validate_chat_question("a" * 1201)[0] is False
    assert validate_chat_question("https://evil.example")[0] is False
    assert validate_chat_question("aaaaaaaaaaaaaaaaaaaa")[0] is False
    ok, err = validate_chat_question("What is reflection of light?")
    assert ok is True
    assert err is None


def test_rate_limit_survives_new_session_same_ip():
    limiter = RateLimiter(
        RateLimitConfig(
            per_ip_max_requests=3,
            per_ip_window_seconds=600,
            per_session_max_requests=10,
            per_session_window_seconds=600,
            min_interval_seconds=0,
            global_max_requests=100,
            global_window_seconds=600,
        )
    )
    assert limiter.allow(ip_key="1.2.3.4", session_key="s1")[0] is True
    assert limiter.allow(ip_key="1.2.3.4", session_key="s2")[0] is True
    assert limiter.allow(ip_key="1.2.3.4", session_key="s3")[0] is True
    allowed, message = limiter.allow(ip_key="1.2.3.4", session_key="s4")
    assert allowed is False
    assert "network" in (message or "").lower()


def test_min_interval_between_requests():
    limiter = RateLimiter(
        RateLimitConfig(
            per_ip_max_requests=20,
            per_ip_window_seconds=600,
            per_session_max_requests=20,
            per_session_window_seconds=600,
            min_interval_seconds=30,
            global_max_requests=100,
            global_window_seconds=600,
        )
    )
    assert limiter.allow(ip_key="9.9.9.9", session_key="a")[0] is True
    allowed, message = limiter.allow(ip_key="9.9.9.9", session_key="a")
    assert allowed is False
    assert "wait" in (message or "").lower()
