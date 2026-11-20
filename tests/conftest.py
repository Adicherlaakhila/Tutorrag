"""Shared pytest fixtures and local-dev answer loading."""

from __future__ import annotations

import os
from pathlib import Path

# Enable gitignored local answer file for tests that need grading.
os.environ.setdefault("TUTORRAG_ALLOW_DEV_ANSWERS", "1")
# Keep usage files out of the repo during tests.
os.environ.setdefault(
    "TUTORRAG_USAGE_PATH",
    str(Path(__file__).resolve().parent / ".usage_test" / "groq_usage.json"),
)
