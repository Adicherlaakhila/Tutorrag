"""ASGI entry point for TutorRAG (Streamlit App).

Cursor / ASGI hosts expect a module-level ``app`` variable.
The Streamlit UI lives in ``streamlit_app.py`` and is unchanged.
Local options:
  - uvicorn app:app --host 0.0.0.0 --port 8501
  - streamlit run streamlit_app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_SCRIPT = Path(__file__).resolve().parent / "streamlit_app.py"

# Official Streamlit ASGI application (not a placeholder).
app = st.App(str(_SCRIPT))
