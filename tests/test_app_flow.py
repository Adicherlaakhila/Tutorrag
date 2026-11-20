"""Streamlit AppTest flows for profile, quiz, and out-of-syllabus chat."""

from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_incomplete_profile_shows_errors():
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    at.run()
    # Submit empty nickname via sidebar form
    at.sidebar.text_input[0].set_value("")
    at.sidebar.button[0].click().run()
    # Validation errors should appear (nickname required)
    assert any("Nickname" in err.value for err in at.error) or any(
        "Nickname" in err.value for err in at.sidebar.error
    )


def test_save_profile_and_generate_quiz():
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    at.run()

    at.sidebar.text_input[0].set_value("Alex")
    # level/subject/topic/style already have defaults in widgets
    at.sidebar.button[0].click().run()

    assert at.session_state["profile"] is not None
    assert at.session_state["profile"]["nickname"] == "Alex"

    # Switch to Practice Quiz tab is automatic via widgets on page;
    # generate quiz using default All topics + Beginner.
    # Find generate button in main area.
    generate_buttons = [b for b in at.button if "Generate" in b.label]
    assert generate_buttons, "Generate quiz button not found"
    generate_buttons[0].click().run()

    assert at.session_state["quiz_questions"] is not None
    assert len(at.session_state["quiz_questions"]) == 5
    assert at.session_state["quiz_error"] is None


def test_out_of_syllabus_chat_without_groq():
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    at.run()
    at.sidebar.text_input[0].set_value("Alex")
    at.sidebar.button[0].click().run()

    at.chat_input[0].set_value(
        "Explain the complete process of human digestion in the stomach."
    ).run()

    messages = at.session_state["messages"]
    assert len(messages) >= 2
    assistant = messages[-1]["content"].lower()
    assert "outside" in assistant or "syllabus" in assistant
