"""Practice quiz helpers with server-side answer lookup."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any

from utils.answer_key import get_answer_key


DEFAULT_QUESTIONS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "questions.csv"
)

_REQUIRED_COLUMNS = {
    "question_id",
    "question",
    "topic",
    "difficulty",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
}
_FORBIDDEN_COLUMNS = {"correct_answer", "explanation"}


def load_question_bank(path: Path | str | None = None) -> list[dict[str, str]]:
    """Load the public question bank (no answer key columns)."""
    csv_path = Path(path) if path else DEFAULT_QUESTIONS_PATH
    if not csv_path.exists():
        raise FileNotFoundError("Question bank is unavailable.")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Question bank is missing required columns.")
        columns = {name.strip() for name in reader.fieldnames}
        missing = _REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError("Question bank is missing required columns.")
        # Refuse to load files that still embed plaintext answer keys.
        if _FORBIDDEN_COLUMNS & columns:
            raise ValueError("Public question bank must not include answer key columns.")

        rows: list[dict[str, str]] = []
        for raw in reader:
            rows.append(
                {
                    "question_id": str(raw.get("question_id", "")).strip(),
                    "question": str(raw.get("question", "")).strip(),
                    "topic": str(raw.get("topic", "")).strip(),
                    "difficulty": str(raw.get("difficulty", "")).strip(),
                    "option_a": str(raw.get("option_a", "")).strip(),
                    "option_b": str(raw.get("option_b", "")).strip(),
                    "option_c": str(raw.get("option_c", "")).strip(),
                    "option_d": str(raw.get("option_d", "")).strip(),
                }
            )
    return rows


def available_topics(bank: list[dict[str, str]]) -> list[str]:
    topics = {row["topic"] for row in bank if row.get("topic")}
    return sorted(topics)


def filter_questions(
    bank: list[dict[str, str]],
    topic: str | None = None,
    difficulty: str | None = None,
) -> list[dict[str, str]]:
    filtered = bank
    if topic:
        topic_key = topic.casefold()
        filtered = [row for row in filtered if row["topic"].casefold() == topic_key]
    if difficulty:
        difficulty_key = difficulty.casefold()
        filtered = [
            row for row in filtered if row["difficulty"].casefold() == difficulty_key
        ]
    return filtered


def select_quiz_questions(
    bank: list[dict[str, str]],
    topic: str | None,
    difficulty: str | None,
    count: int = 5,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """
    Select exactly `count` random questions matching topic and difficulty.

    Returned question objects intentionally omit correct answers/explanations.
    Grading resolves those server-side from the private answer key.
    """
    filtered = filter_questions(bank, topic=topic, difficulty=difficulty)
    # Only keep items that exist in the server answer key.
    answer_key = get_answer_key()
    filtered = [row for row in filtered if row["question_id"] in answer_key]
    if len(filtered) < count:
        label_topic = topic or "any topic"
        label_level = difficulty or "any level"
        return None, (
            f"Not enough questions for topic '{label_topic}' at '{label_level}' level. "
            f"Found {len(filtered)}, need {count}. Try another topic or level, "
            "or clear the topic filter to use the full unit."
        )

    sample = random.sample(filtered, k=count)
    questions: list[dict[str, Any]] = []
    for row in sample:
        questions.append(
            {
                "question_id": str(row["question_id"]),
                "question": str(row["question"]),
                "topic": str(row["topic"]),
                "difficulty": str(row["difficulty"]),
                "options": {
                    "A": str(row["option_a"]),
                    "B": str(row["option_b"]),
                    "C": str(row["option_c"]),
                    "D": str(row["option_d"]),
                },
            }
        )
    return questions, None


def grade_quiz(
    questions: list[dict[str, Any]],
    answers: dict[str, str],
) -> dict[str, Any]:
    """Grade submitted answers using the server-side answer key only."""
    details = []
    score = 0
    for question in questions:
        qid = question["question_id"]
        selected = str(answers.get(qid, "")).strip().upper()
        key = get_answer_key().get(qid)
        if not key:
            details.append(
                {
                    "question_id": qid,
                    "question": question["question"],
                    "selected": selected or None,
                    "correct_answer": None,
                    "is_correct": False,
                    "explanation": "Answer key unavailable for this question.",
                    "options": question["options"],
                }
            )
            continue

        correct = str(key["correct_answer"]).upper()
        explanation = str(key["explanation"])
        is_correct = selected == correct and selected in {"A", "B", "C", "D"}
        if is_correct:
            score += 1
        details.append(
            {
                "question_id": qid,
                "question": question["question"],
                "selected": selected or None,
                "correct_answer": correct,
                "is_correct": is_correct,
                "explanation": explanation,
                "options": question["options"],
            }
        )
    return {
        "score": score,
        "total": len(questions),
        "details": details,
    }
