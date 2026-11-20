"""Live Groq API tests – skipped automatically when GROQ_API_KEY is absent."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from rag.tutor import TutorService  # noqa: E402


pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not configured",
)


@pytest.fixture(scope="module")
def tutor() -> TutorService:
    return TutorService()


def test_beginner_reflection_answer(tutor: TutorService):
    profile = {
        "nickname": "Sam",
        "level": "Beginner",
        "subject": "Class 10 Science",
        "topic": "Light – Reflection and Refraction",
        "style": "Simple Explanation",
    }
    result = tutor.answer("What is reflection of light?", profile)
    assert result["is_relevant"] is True
    assert result["sources"]
    assert "Source:" in result["sources"][0]["label"]
    assert len(result["answer"]) > 40


def test_advanced_reflection_answer(tutor: TutorService):
    profile = {
        "nickname": "Sam",
        "level": "Advanced",
        "subject": "Class 10 Science",
        "topic": "Light – Reflection and Refraction",
        "style": "Exam-Focused Answers",
    }
    result = tutor.answer("What is reflection of light?", profile)
    assert result["is_relevant"] is True
    assert result["sources"]


def test_out_of_syllabus_digestion(tutor: TutorService):
    profile = {
        "nickname": "Sam",
        "level": "Intermediate",
        "subject": "Class 10 Science",
        "topic": "Light – Reflection and Refraction",
        "style": "Simple Explanation",
    }
    result = tutor.answer(
        "Explain the complete process of human digestion.",
        profile,
    )
    assert result["is_relevant"] is False
    assert "outside" in result["answer"].lower() or "syllabus" in result["answer"].lower()


def test_homework_integrity(tutor: TutorService):
    profile = {
        "nickname": "Sam",
        "level": "Intermediate",
        "subject": "Class 10 Science",
        "topic": "Light – Reflection and Refraction",
        "style": "Simple Explanation",
    }
    result = tutor.answer(
        "Write my homework on laws of reflection and give me the full answer to submit.",
        profile,
    )
    assert result["integrity_flag"] is True
    lowered = result["answer"].lower()
    assert any(
        word in lowered
        for word in ("hint", "step", "try", "attempt", "review", "yourself")
    )
