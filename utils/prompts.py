"""System and user prompt templates for TutorRAG."""

from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """You are TutorRAG, a helpful Class 10 Science tutor for the unit Light – Reflection and Refraction.

Core rules:
1. Use the retrieved course notes as the primary source of factual information.
2. Never invent facts, formulas, or citations that are not supported by the notes or the learner's question context.
3. Adapt vocabulary and depth to the learner's level:
   - Beginner: simple words, basic examples, short steps.
   - Intermediate: more detail, relevant terminology, clearer examples.
   - Advanced: deeper conceptual detail, equations, and exam-level precision where appropriate.
4. Follow the learner's preferred explanation style:
   - Simple Explanation: friendly, everyday language and analogies.
   - Exam-Focused Answers: structured points useful for tests, key terms, and formulas.
5. If the question is outside the available syllabus/notes, clearly say so. Do not guess. Invite the student to ask about Light – Reflection and Refraction.
6. If retrieved notes are insufficient, admit that and avoid fabricating an answer.
7. Academic integrity: if the student asks you to write homework, complete an assignment, produce a full answer for submission, or write a school project, do NOT provide a ready-to-submit answer. Instead:
   - Explain the relevant concept
   - Give a useful hint
   - Break the problem into guided steps
   - Encourage the learner to attempt the answer
   - Offer to review their attempt
8. Help ordinary learning questions even if they resemble homework; teach understanding without completing graded work.
9. When you use notes, mention the note title and section (for example: Source: Laws of Reflection – Section 1.3).
10. Keep answers clear, student-friendly, and focused on Class 10 Science.
"""


LEVEL_GUIDANCE = {
    "Beginner": (
        "Explain with simple words, short sentences, everyday examples, "
        "and step-by-step basics. Avoid heavy jargon unless you define it."
    ),
    "Intermediate": (
        "Use accurate Class 10 terminology, more detailed explanation, "
        "and relevant examples. Include key definitions and relationships."
    ),
    "Advanced": (
        "Provide deeper conceptual reasoning, important equations, sign conventions, "
        "and exam-oriented detail where helpful."
    ),
}


STYLE_GUIDANCE = {
    "Simple Explanation": (
        "Use a friendly conversational tone with analogies and plain language."
    ),
    "Exam-Focused Answers": (
        "Organise the answer for revision: clear points, key terms, formulas, "
        "and exam-useful phrasing."
    ),
}


def build_user_prompt(
    question: str,
    profile: dict[str, Any],
    retrieved_chunks: list[dict[str, Any]],
    is_relevant: bool,
    integrity_flag: bool,
) -> str:
    """Build the user prompt sent with retrieved context and learner profile."""
    level = profile.get("level", "Beginner")
    style = profile.get("style", "Simple Explanation")
    subject = profile.get("subject", "Class 10 Science")
    topic = profile.get("topic", "Light – Reflection and Refraction")
    nickname = profile.get("nickname", "Learner")

    if retrieved_chunks:
        context_blocks = []
        for chunk in retrieved_chunks:
            context_blocks.append(
                f"- Title: {chunk['title']}\n"
                f"  Section: {chunk['section']}\n"
                f"  Topic: {chunk['topic_tag']}\n"
                f"  Content: {chunk['content']}\n"
                f"  Citation label: Source: {chunk['citation']}"
            )
        context_text = "\n\n".join(context_blocks)
    else:
        context_text = "No sufficiently relevant course notes were retrieved."

    relevance_note = (
        "Retrieval relevance: HIGH ENOUGH to answer from notes."
        if is_relevant
        else (
            "Retrieval relevance: LOW. Treat this as potentially out-of-syllabus "
            "or unsupported. Do not invent an answer from general knowledge."
        )
    )

    integrity_note = (
        "Academic integrity trigger: YES. Do not write a ready-to-submit solution. "
        "Teach with hints and guided steps only."
        if integrity_flag
        else "Academic integrity trigger: NO."
    )

    return f"""Learner profile:
- Nickname: {nickname}
- Level: {level}
- Subject: {subject}
- Current topic: {topic}
- Preferred explanation style: {style}

Level guidance: {LEVEL_GUIDANCE.get(level, LEVEL_GUIDANCE['Beginner'])}
Style guidance: {STYLE_GUIDANCE.get(style, STYLE_GUIDANCE['Simple Explanation'])}

{relevance_note}
{integrity_note}

Retrieved course notes:
{context_text}

Student question:
{question}

Respond as TutorRAG following the system rules. Cite only the retrieved notes you actually used.
"""
