"""Server-only secret helpers. Never send these values to the browser UI."""

from __future__ import annotations

import os
from typing import Any


def get_secret(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if secrets is not None and name in secrets:
            raw = secrets[name]
            if isinstance(raw, dict):
                return ""
            return str(raw).strip()
    except Exception:
        return default
    return default


def get_secret_any(name: str) -> Any | None:
    env = os.getenv(name)
    if env is not None and str(env).strip() != "":
        return env
    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if secrets is not None and name in secrets:
            return secrets[name]
    except Exception:
        return None
    return None


def is_production() -> bool:
    flag = get_secret("TUTORRAG_ENV", os.getenv("ENV", "")).strip().lower()
    if flag in {"prod", "production"}:
        return True
    # Cursor / Streamlit Cloud usually inject host markers; treat missing access
    # as local unless explicitly production.
    if get_secret("TUTORRAG_DISABLE_DEV_ANSWERS") == "1":
        return True
    return False
