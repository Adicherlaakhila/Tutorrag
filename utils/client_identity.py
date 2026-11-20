"""Resolve client identity for server-side abuse controls."""

from __future__ import annotations

from utils.rate_limit import fingerprint_client


def resolve_client_ip() -> str:
    """
    Best-effort client IP from Streamlit request context.

    Do not trust client-supplied X-Forwarded-For as a sole identity.
    If platform IP is missing, fall back to a shared unknown bucket.
    """
    try:
        import streamlit as st

        context = getattr(st, "context", None)
        if context is None:
            return "unknown-ip"
        ip = getattr(context, "ip_address", None)
        if ip:
            return str(ip).strip() or "unknown-ip"
    except Exception:
        return "unknown-ip"
    return "unknown-ip"


def resolve_user_agent() -> str:
    try:
        import streamlit as st

        headers = getattr(getattr(st, "context", None), "headers", None) or {}
        return str(headers.get("User-Agent") or headers.get("user-agent") or "")
    except Exception:
        return ""


def resolve_client_bucket() -> str:
    """Stable abuse-control key: platform IP, else hashed unknown+UA fingerprint."""
    ip = resolve_client_ip()
    if ip != "unknown-ip":
        return ip
    return f"fp:{fingerprint_client('unknown-ip', resolve_user_agent())}"
