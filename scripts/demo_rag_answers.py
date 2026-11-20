"""Demonstrate retrieval + citation formatting for beginner/advanced profiles.

This script verifies that the same doubt retrieves real notes and that
level/style are passed into the prompt builder. It does not invent citations.
If GROQ_API_KEY is available, it also prints live model answers.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from rag.chunking import notes_to_chunks
from rag.loader import load_notes
from rag.retrieval import TFIDFRetriever
from rag.tutor import TutorService
from utils.prompts import build_user_prompt


QUESTION = "What is reflection of light?"


def show_retrieval() -> None:
    notes = load_notes()
    chunks = notes_to_chunks(notes)
    retriever = TFIDFRetriever(chunks)
    result = retriever.retrieve(QUESTION, top_k=3)
    print("Query:", QUESTION)
    print("Relevant:", result.is_relevant, "max_score:", round(result.max_score, 4))
    for chunk in result.chunks:
        print(f"- Source: {chunk['citation']} (score={chunk['score']})")
    return result


def main() -> None:
    result = show_retrieval()
    for level, style in [
        ("Beginner", "Simple Explanation"),
        ("Advanced", "Exam-Focused Answers"),
    ]:
        profile = {
            "nickname": "Alex",
            "level": level,
            "subject": "Class 10 Science",
            "topic": "Light – Reflection and Refraction",
            "style": style,
        }
        prompt = build_user_prompt(
            QUESTION,
            profile,
            result.chunks,
            result.is_relevant,
            integrity_flag=False,
        )
        print("\n" + "=" * 60)
        print(f"PROFILE: {level} / {style}")
        print("Prompt includes level guidance:", level in prompt)
        print("Citations in prompt:", all(c["title"] in prompt for c in result.chunks))

    if not os.getenv("GROQ_API_KEY"):
        print("\nGROQ_API_KEY not set – skipping live LLM answers.")
        return

    tutor = TutorService()
    for level, style in [
        ("Beginner", "Simple Explanation"),
        ("Advanced", "Exam-Focused Answers"),
    ]:
        profile = {
            "nickname": "Alex",
            "level": level,
            "subject": "Class 10 Science",
            "topic": "Light – Reflection and Refraction",
            "style": style,
        }
        answer = tutor.answer(QUESTION, profile)
        print("\n" + "=" * 60)
        print(f"LIVE ANSWER ({level})")
        print(answer["answer"][:500])
        print("Sources:", [s["label"] for s in answer["sources"]])


if __name__ == "__main__":
    main()
