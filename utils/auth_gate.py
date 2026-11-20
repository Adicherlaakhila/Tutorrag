"""Lightweight shared access-code authentication for public deployments."""

from __future__ import annotations

import hashlib
import hmac

from utils.secrets_util import get_secret


def access_code_configured() -> bool:
    return bool(get_secret("APP_ACCESS_CODE"))


def groq_configured() -> bool:
    return bool(get_secret("GROQ_API_KEY"))


def auth_required() -> bool:
    """
    Require unlock when a class code exists, or when Groq is configured
    (paid API path must not be anonymously open).
    """
    return access_code_configured() or groq_configured()


def verify_access_code(candidate: str) -> bool:
    expected = get_secret("APP_ACCESS_CODE")
    if not expected:
        # Notes-only local mode (no Groq): allow.
        if not groq_configured():
            return True
        # Groq is configured but no access code was set by the operator.
        return False
    provided = (candidate or "").strip()
    if not provided:
        return False
    return hmac.compare_digest(
        hashlib.sha256(provided.encode("utf-8")).digest(),
        hashlib.sha256(expected.encode("utf-8")).digest(),
    )
