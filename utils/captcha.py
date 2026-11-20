"""Server-side math CAPTCHA (bot friction without a third-party widget)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass

from utils.secrets_util import get_secret


def _captcha_pepper() -> bytes:
    configured = (get_secret("CAPTCHA_PEPPER") or os.getenv("CAPTCHA_PEPPER", "")).strip()
    if configured:
        return configured.encode("utf-8")
    # Stable for process lifetime only (dev / single-worker).
    if not hasattr(_captcha_pepper, "_value"):
        setattr(_captcha_pepper, "_value", secrets.token_bytes(32))
    return getattr(_captcha_pepper, "_value")


def captcha_pepper_configured() -> bool:
    return bool((get_secret("CAPTCHA_PEPPER") or os.getenv("CAPTCHA_PEPPER", "")).strip())


def captcha_ready_for_groq() -> bool:
    """Public Groq path should use a shared pepper across workers."""
    return captcha_pepper_configured()


@dataclass
class CaptchaChallenge:
    prompt: str
    token: str
    expires_at: float


def issue_math_captcha(ttl_seconds: int = 300) -> CaptchaChallenge:
    # Multiplication yields a larger answer space than tiny addition sums.
    a = secrets.randbelow(9) + 4  # 4..12
    b = secrets.randbelow(9) + 4  # 4..12
    answer = str(a * b)
    nonce = secrets.token_hex(8)
    expires_at = time.time() + ttl_seconds
    material = f"{nonce}:{answer}:{int(expires_at)}".encode("utf-8")
    token = hmac.new(_captcha_pepper(), material, hashlib.sha256).hexdigest()
    packed = f"{nonce}.{int(expires_at)}.{token}"
    return CaptchaChallenge(
        prompt=f"What is {a} × {b}?",
        token=packed,
        expires_at=expires_at,
    )


def verify_math_captcha(token: str, user_answer: str) -> bool:
    try:
        nonce, exp_s, sig = (token or "").split(".", 2)
        expires_at = int(exp_s)
    except ValueError:
        return False
    if time.time() > expires_at:
        return False
    answer = str(user_answer or "").strip()
    if not answer.isdigit():
        return False
    material = f"{nonce}:{answer}:{expires_at}".encode("utf-8")
    expected = hmac.new(_captcha_pepper(), material, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
