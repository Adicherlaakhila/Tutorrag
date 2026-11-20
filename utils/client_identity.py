"""Resolve client identity for server-side abuse controls."""

from __future__ import annotations


def resolve_client_ip() -> str:
    """Best-effort client IP from Streamlit request context."""
    try:
        import streamlit as st

        context = getattr(st, "context", None)
        if context is None:
            return "unknown-ip"
        ip = getattr(context, "ip_address", None)
        if ip:
            return str(ip).strip() or "unknown-ip"
        headers = getattr(context, "headers", None) or {}
        forwarded = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for")
        if forwarded:
            return str(forwarded).split(",")[0].strip() or "unknown-ip"
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
