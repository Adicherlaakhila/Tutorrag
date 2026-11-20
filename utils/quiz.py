"""Practice quiz helpers backed by the CSV question bank."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_QUESTION_BANK = (
    Path(__file__).resolve().parent.parent / "data" / "question_bank.csv"
)


def load_question_bank(path: Path | str | None = None) -> pd.DataFrame:
    csv_path = Path(path) if path else DEFAULT_QUESTION_BANK
    if not csv_path.exists():
        raise FileNotFoundError(f"Question bank not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required = {
        "question_id",
        "question",
        "topic",
        "difficulty",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_answer",
        "explanation",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Question bank missing columns: {sorted(missing)}")

    df = df.copy()
    df["difficulty"] = df["difficulty"].astype(str).str.strip()
    df["topic"] = df["topic"].astype(str).str.strip()
    df["correct_answer"] = df["correct_answer"].astype(str).str.strip().str.upper()
    return df


def available_topics(df: pd.DataFrame) -> list[str]:
    return sorted(df["topic"].dropna().unique().tolist())


def filter_questions(
    df: pd.DataFrame,
    topic: str | None = None,
    difficulty: str | None = None,
) -> pd.DataFrame:
    filtered = df
    if topic:
        filtered = filtered[filtered["topic"].str.casefold() == topic.casefold()]
    if difficulty:
        filtered = filtered[
            filtered["difficulty"].str.casefold() == difficulty.casefold()
        ]
    return filtered.reset_index(drop=True)


def select_quiz_questions(
    df: pd.DataFrame,
    topic: str | None,
    difficulty: str | None,
    count: int = 5,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """
    Select exactly `count` random questions matching topic and difficulty.

    Returns (questions, error_message).
    """
    filtered = filter_questions(df, topic=topic, difficulty=difficulty)
    if len(filtered) < count:
        label_topic = topic or "any topic"
        label_level = difficulty or "any level"
        return None, (
            f"Not enough questions for topic '{label_topic}' at '{label_level}' level. "
            f"Found {len(filtered)}, need {count}. Try another topic or level, "
            "or clear the topic filter to use the full unit."
        )

    sample = filtered.sample(n=count).reset_index(drop=True)
    questions: list[dict[str, Any]] = []
    for _, row in sample.iterrows():
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
                "correct_answer": str(row["correct_answer"]).upper(),
                "explanation": str(row["explanation"]),
            }
        )
    return questions, None


def grade_quiz(
    questions: list[dict[str, Any]],
    answers: dict[str, str],
) -> dict[str, Any]:
    """Grade submitted answers and build per-question feedback."""
    details = []
    score = 0
    for question in questions:
        qid = question["question_id"]
        selected = str(answers.get(qid, "")).strip().upper()
        correct = question["correct_answer"]
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
                "explanation": question["explanation"],
                "options": question["options"],
            }
        )
    return {
        "score": score,
        "total": len(questions),
        "details": details,
    }
