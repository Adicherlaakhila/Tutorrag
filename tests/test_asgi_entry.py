"""Verify the publisher ASGI entry point is a real Streamlit App."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_app_exports_streamlit_asgi_app():
    from app import app

    assert type(app).__name__ == "App"
    assert "streamlit" in type(app).__module__
    assert Path(app.script_path).name == "streamlit_app.py"
    assert Path(app.script_path).is_file()
