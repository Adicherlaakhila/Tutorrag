"""Unit and integration-style tests for TutorRAG core features."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag.chunking import notes_to_chunks
from rag.loader import load_notes
from rag.retrieval import TFIDFRetriever
from utils.answer_key import get_answer_key
from utils.quiz import grade_quiz, load_question_bank, select_quiz_questions
from utils.rate_limit import RateLimitConfig, RateLimiter
from utils.validation import is_homework_request, validate_profile


def test_notes_count_and_fields():
    notes = load_notes()
    assert 10 <= len(notes) <= 15
    for note in notes:
        assert note["note_id"]
        assert note["title"]
        assert note["topic_tag"]
        assert note["section"]
        assert note["content"]


def test_tfidf_retrieves_reflection_notes():
    notes = load_notes()
    chunks = notes_to_chunks(notes)
    retriever = TFIDFRetriever(chunks)
    result = retriever.retrieve("What are the laws of reflection?", top_k=3)
    assert result.is_relevant
    assert len(result.chunks) <= 3
    citations = " ".join(c["title"].lower() for c in result.chunks)
    assert "reflection" in citations


def test_out_of_syllabus_low_relevance():
    notes = load_notes()
    chunks = notes_to_chunks(notes)
    retriever = TFIDFRetriever(chunks)
    result = retriever.retrieve(
        "Explain the complete process of human digestion in the stomach and intestines.",
        top_k=3,
    )
    assert result.max_score < 0.25 or not result.is_relevant


def test_profile_validation_missing_fields():
    ok, errors, profile = validate_profile("", "", "", "", "")
    assert not ok
    assert profile is None
    assert any("Nickname" in e for e in errors)


def test_profile_validation_success():
    ok, errors, profile = validate_profile(
        "Akhila",
        "Beginner",
        "Class 10 Science",
        "Light – Reflection and Refraction",
        "Simple Explanation",
    )
    assert ok
    assert not errors
    assert profile["nickname"] == "Akhila"


def test_homework_detection():
    assert is_homework_request("Please write my homework on mirrors")
    assert is_homework_request("Complete my assignment tonight")
    assert not is_homework_request("What is the mirror formula?")


def test_question_bank_has_no_answer_columns():
    df = load_question_bank()
    assert 30 <= len(df) <= 50
    assert "correct_answer" not in df.columns
    assert "explanation" not in df.columns
    # Local/dev answer file or QUIZ_ANSWER_BANK may provide keys for grading tests.
    assert len(get_answer_key()) >= 1


def test_question_bank_size_and_quiz():
    df = load_question_bank()
    questions, error = select_quiz_questions(
        df, topic=None, difficulty="Beginner", count=5
    )
    assert error is None
    assert questions is not None
    assert len(questions) == 5
    for q in questions:
        assert "correct_answer" not in q
        assert "explanation" not in q


def test_quiz_insufficient_questions_message():
    df = load_question_bank()
    questions, error = select_quiz_questions(
        df,
        topic="Introduction to Light",
        difficulty="Advanced",
        count=5,
    )
    if questions is None:
        assert error is not None
        assert "Not enough questions" in error


def test_quiz_grading_uses_server_answer_key():
    questions = [
        {
            "question_id": "Q01",
            "question": "What is light?",
            "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
        },
        {
            "question_id": "Q02",
            "question": "Speed of light?",
            "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
        },
    ]
    result = grade_quiz(questions, {"Q01": "A", "Q02": "C"})
    assert result["score"] == 1
    assert result["total"] == 2
    assert result["details"][0]["is_correct"] is True
    assert result["details"][1]["is_correct"] is False
    assert result["details"][1]["correct_answer"] == get_answer_key()["Q02"]["correct_answer"]


def test_beginner_and_advanced_same_query_retrieve_same_sources():
    notes = load_notes()
    chunks = notes_to_chunks(notes)
    retriever = TFIDFRetriever(chunks)
    query = "What is reflection of light?"
    beginner = retriever.retrieve(query, top_k=3)
    advanced = retriever.retrieve(query, top_k=3)
    assert beginner.is_relevant and advanced.is_relevant
    assert [c["note_id"] for c in beginner.chunks] == [
        c["note_id"] for c in advanced.chunks
    ]


def test_notes_fallback_adapts_level_and_cites():
    from rag.tutor import TutorService

    tutor = TutorService()
    base_profile = {
        "nickname": "Alex",
        "subject": "Class 10 Science",
        "topic": "Light – Reflection and Refraction",
        "style": "Simple Explanation",
    }
    beginner = tutor.answer(
        "What is reflection of light?",
        {**base_profile, "level": "Beginner", "style": "Simple Explanation"},
        client_key="test-beginner",
        authenticated=True,
    )
    advanced = tutor.answer(
        "What is reflection of light?",
        {**base_profile, "level": "Advanced", "style": "Exam-Focused Answers"},
        client_key="test-advanced",
        authenticated=True,
    )
    assert beginner["is_relevant"] and advanced["is_relevant"]
    assert beginner["sources"] and "Source:" in beginner["sources"][0]["label"]
    assert "simple" in beginner["answer"].lower() or "Hi Alex" in beginner["answer"]
    assert "Advanced" in advanced["answer"] or "exam" in advanced["answer"].lower()
    assert beginner["answer"] != advanced["answer"]


def test_homework_integrity_fallback():
    from rag.tutor import TutorService

    tutor = TutorService()
    result = tutor.answer(
        "Write my homework on laws of reflection and give me the full answer to submit.",
        {
            "nickname": "Alex",
            "level": "Intermediate",
            "subject": "Class 10 Science",
            "topic": "Light – Reflection and Refraction",
            "style": "Simple Explanation",
        },
        client_key="test-homework",
        authenticated=True,
    )
    assert result["integrity_flag"] is True
    assert "ready-to-submit" in result["answer"].lower()
    assert "guided steps" in result["answer"].lower()


def test_rate_limiter_blocks_excess_requests():
    limiter = RateLimiter(
        RateLimitConfig(
            per_ip_max_requests=3,
            per_ip_window_seconds=600,
            per_session_max_requests=3,
            per_session_window_seconds=600,
            min_interval_seconds=0,
            global_max_requests=100,
            global_window_seconds=600,
        )
    )
    assert limiter.allow(ip_key="10.0.0.1", session_key="user-a", enforce_budget=False)[0]
    assert limiter.allow(ip_key="10.0.0.1", session_key="user-a", enforce_budget=False)[0]
    assert limiter.allow(ip_key="10.0.0.1", session_key="user-a", enforce_budget=False)[0]
    allowed, message = limiter.allow(
        ip_key="10.0.0.1", session_key="user-a", enforce_budget=False
    )
    assert allowed is False
    assert message is not None
    assert "limit" in message.lower()


def test_privacy_safe_profile_redacts_nickname():
    from rag.tutor import TutorService

    tutor = TutorService()
    safe = tutor._privacy_safe_profile(
        {
            "nickname": "Alex",
            "level": "Beginner",
            "subject": "Class 10 Science",
            "topic": "Light – Reflection and Refraction",
            "style": "Simple Explanation",
        }
    )
    assert safe["nickname"] == "Learner"
    assert safe["level"] == "Beginner"
