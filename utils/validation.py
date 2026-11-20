"""Validation helpers for learner profile and chat input."""

from __future__ import annotations

from typing import Any


VALID_LEVELS = ("Beginner", "Intermediate", "Advanced")
VALID_STYLES = ("Simple Explanation", "Exam-Focused Answers")
DEFAULT_SUBJECT = "Class 10 Science"
DEFAULT_TOPIC = "Light – Reflection and Refraction"

HOMEWORK_PATTERNS = (
    "write my homework",
    "do my homework",
    "complete my homework",
    "complete my assignment",
    "finish my assignment",
    "write my assignment",
    "give me the full answer to submit",
    "answer to submit",
    "write my school project",
    "do my project for me",
    "complete my project",
    "write the entire answer for submission",
    "give me the ready answer to submit",
)


def validate_profile(
    nickname: str,
    level: str,
    subject: str,
    topic: str,
    style: str,
) -> tuple[bool, list[str], dict[str, str] | None]:
    """Validate learner profile fields and return cleaned profile data."""
    errors: list[str] = []
    cleaned_nickname = (nickname or "").strip()
    cleaned_subject = (subject or "").strip()
    cleaned_topic = (topic or "").strip()
    cleaned_level = (level or "").strip()
    cleaned_style = (style or "").strip()

    if not cleaned_nickname:
        errors.append("Nickname is required.")
    elif len(cleaned_nickname) < 2:
        errors.append("Nickname must be at least 2 characters.")

    if cleaned_level not in VALID_LEVELS:
        errors.append("Please select a valid learning level.")

    if not cleaned_subject:
        errors.append("Subject is required.")

    if not cleaned_topic:
        errors.append("Current topic is required.")

    if cleaned_style not in VALID_STYLES:
        errors.append("Please select a preferred explanation style.")

    if errors:
        return False, errors, None

    profile = {
        "nickname": cleaned_nickname,
        "level": cleaned_level,
        "subject": cleaned_subject,
        "topic": cleaned_topic,
        "style": cleaned_style,
    }
    return True, [], profile


def is_homework_request(text: str) -> bool:
    """Detect graded-work completion requests without blocking normal learning."""
    lowered = " ".join((text or "").lower().split())
    return any(pattern in lowered for pattern in HOMEWORK_PATTERNS)


def profile_summary(profile: dict[str, Any] | None) -> str:
    if not profile:
        return "No learner profile saved yet."
    return (
        f"{profile.get('nickname', 'Learner')} · {profile.get('level', '-')} · "
        f"{profile.get('subject', '-')} · {profile.get('topic', '-')} · "
        f"{profile.get('style', '-')}"
    )
