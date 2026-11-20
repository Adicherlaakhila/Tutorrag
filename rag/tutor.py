"""Groq-backed tutoring service with RAG context and rate limiting."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from rag.chunking import notes_to_chunks
from rag.loader import load_notes
from rag.retrieval import TFIDFRetriever
from utils.captcha import verify_math_captcha
from utils.prompts import SYSTEM_PROMPT, build_user_prompt
from utils.rate_limit import GROQ_RATE_LIMITER
from utils.validation import is_homework_request, validate_chat_question

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class TutorService:
    """End-to-end doubt answering with retrieval + Groq generation."""

    def __init__(self) -> None:
        load_dotenv()
        notes = load_notes()
        chunks = notes_to_chunks(notes)
        self.retriever = TFIDFRetriever(chunks)
        self.notes = notes
        self.chunks = chunks
        self.model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
        self._client: Groq | None = None

    def get_api_key(self) -> str | None:
        """Resolve Groq API key from environment or Streamlit secrets."""
        key = os.getenv("GROQ_API_KEY", "").strip()
        if key:
            return key
        try:
            import streamlit as st

            secrets = getattr(st, "secrets", None)
            if secrets is not None and "GROQ_API_KEY" in secrets:
                return str(secrets["GROQ_API_KEY"]).strip() or None
        except Exception:
            return None
        return None

    def _client_or_none(self) -> Groq | None:
        api_key = self.get_api_key()
        if not api_key:
            return None
        if self._client is None:
            self._client = Groq(api_key=api_key)
        return self._client

    def _sources_from_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()
        for chunk in chunks:
            label = f"Source: {chunk['citation']}"
            if label not in seen:
                sources.append(
                    {
                        "label": label,
                        "title": chunk["title"],
                        "section": chunk["section"],
                        "score": chunk.get("score"),
                    }
                )
                seen.add(label)
        return sources

    def _privacy_safe_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Send minimal learner context to third-party LLM (no nickname)."""
        return {
            "nickname": "Learner",
            "level": profile.get("level", "Beginner"),
            "subject": profile.get("subject", "Class 10 Science"),
            "topic": profile.get("topic", "Light – Reflection and Refraction"),
            "style": profile.get("style", "Simple Explanation"),
        }

    def _integrity_fallback(self, profile: dict[str, Any], chunks: list[dict[str, Any]]) -> str:
        level = profile.get("level", "Beginner")
        hint = ""
        if chunks:
            hint = chunks[0]["content"].split(".")[0] + "."
        return (
            "I can help you learn, but I will not write a ready-to-submit homework, "
            "assignment, or school project answer.\n\n"
            f"**Concept hint ({level}):** {hint or 'Revisit the key definition from your notes first.'}\n\n"
            "**Guided steps:**\n"
            "1. Write the definitions/laws in your own words.\n"
            "2. Add one simple example or ray-diagram idea.\n"
            "3. Check formulas and sign conventions if the question needs them.\n"
            "4. Attempt your answer.\n\n"
            "Share your attempt and I can review it with you."
        )

    def _notes_fallback(
        self,
        question: str,
        profile: dict[str, Any],
        chunks: list[dict[str, Any]],
        integrity_flag: bool,
    ) -> str:
        """Build a grounded answer from retrieved notes when Groq is unavailable."""
        if integrity_flag:
            return self._integrity_fallback(profile, chunks)

        level = profile.get("level", "Beginner")
        style = profile.get("style", "Simple Explanation")
        primary = chunks[0]
        citation = f"Source: {primary['citation']}"
        display_name = profile.get("nickname", "learner")

        if level == "Beginner":
            body = (
                f"Hi {display_name}! Let's keep this simple.\n\n"
                f"{primary['content']}\n\n"
                "In short: focus on the main idea above and try explaining it in one or two sentences "
                "using your own words."
            )
        elif level == "Advanced":
            extra = "\n\n".join(f"- {c['content']}" for c in chunks[:3])
            body = (
                f"Advanced view for **{question}**:\n\n"
                f"{extra}\n\n"
                "For exams, state definitions precisely, mention related formulas/sign conventions "
                "where relevant, and support your answer with a neat ray diagram when asked."
            )
        else:
            body = (
                f"Here is a clear Class 10 explanation of your doubt.\n\n"
                f"{primary['content']}\n\n"
                "Key terms from the notes are important for both understanding and exams."
            )

        style_note = (
            "\n\n*(Simple Explanation style)*"
            if style.startswith("Simple")
            else "\n\n*(Exam-Focused style: remember definitions, laws, and formulas.)*"
        )
        return (
            f"{body}{style_note}\n\n"
            f"{citation}\n\n"
            "_Answer grounded in retrieved TutorRAG course notes "
            "(Groq LLM activates automatically when GROQ_API_KEY is configured)._"
        )

    def answer(
        self,
        question: str,
        profile: dict[str, Any],
        history: list[dict[str, str]] | None = None,
        client_key: str | None = None,
        client_ip: str | None = None,
        captcha_token: str | None = None,
        captcha_answer: str | None = None,
        authenticated: bool = False,
    ) -> dict[str, Any]:
        ok, validation_error = validate_chat_question(question)
        if not ok:
            return {
                "answer": validation_error or "Please enter a valid Science doubt.",
                "sources": [],
                "is_relevant": False,
                "integrity_flag": False,
                "retrieval_scores": [],
                "mode": "invalid",
            }

        if not authenticated:
            return {
                "answer": (
                    "Please unlock TutorRAG with the class access code before using "
                    "AI tutoring."
                ),
                "sources": [],
                "is_relevant": False,
                "integrity_flag": False,
                "retrieval_scores": [],
                "mode": "unauthorized",
            }

        question = question.strip()
        integrity_flag = is_homework_request(question)
        retrieval = self.retriever.retrieve(question, top_k=3)

        if not retrieval.is_relevant and not integrity_flag:
            return {
                "answer": (
                    "This question appears to be outside the available TutorRAG "
                    f"syllabus notes for **{profile.get('topic', 'Light – Reflection and Refraction')}**. "
                    "I can only teach from the loaded Class 10 Science notes on "
                    "Light – Reflection and Refraction. Please ask a question related "
                    "to that unit, for example reflection, mirrors, refraction, lenses, "
                    "or refractive index."
                ),
                "sources": [],
                "is_relevant": False,
                "integrity_flag": False,
                "retrieval_scores": retrieval.scores,
                "mode": "out_of_syllabus",
            }

        sources = self._sources_from_chunks(retrieval.chunks if retrieval.is_relevant else [])

        client = self._client_or_none()
        if client is None:
            return {
                "answer": self._notes_fallback(
                    question,
                    profile,
                    retrieval.chunks if retrieval.is_relevant else [],
                    integrity_flag,
                ),
                "sources": sources,
                "is_relevant": retrieval.is_relevant,
                "integrity_flag": integrity_flag,
                "retrieval_scores": retrieval.scores,
                "mode": "notes_fallback",
            }

        # Paid Groq path requires a fresh CAPTCHA + rate/budget checks.
        if not verify_math_captcha(captcha_token or "", captcha_answer or ""):
            return {
                "answer": (
                    "Please solve the security check correctly before asking the AI tutor."
                ),
                "sources": sources,
                "is_relevant": retrieval.is_relevant,
                "integrity_flag": integrity_flag,
                "retrieval_scores": retrieval.scores,
                "mode": "captcha_failed",
            }

        allowed, limit_message = GROQ_RATE_LIMITER.allow(
            ip_key=client_ip or "unknown-ip",
            session_key=client_key or "anonymous",
            enforce_budget=True,
        )
        if not allowed:
            return {
                "answer": limit_message
                or "Please wait a moment before sending another tutoring request.",
                "sources": sources,
                "is_relevant": retrieval.is_relevant,
                "integrity_flag": integrity_flag,
                "retrieval_scores": retrieval.scores,
                "mode": "rate_limited",
            }

        safe_profile = self._privacy_safe_profile(profile)
        user_prompt = build_user_prompt(
            question=question,
            profile=safe_profile,
            retrieved_chunks=retrieval.chunks if retrieval.is_relevant else [],
            is_relevant=retrieval.is_relevant,
            integrity_flag=integrity_flag,
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            # Send only the latest user/assistant pair to reduce third-party data sharing.
            for turn in history[-2:]:
                role = turn.get("role")
                content = turn.get("content")
                if role in {"user", "assistant"} and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=900,
            )
            answer_text = response.choices[0].message.content or (
                "I could not generate an answer right now. Please try again."
            )
        except Exception:
            logger.exception("Groq chat completion failed")
            return {
                "answer": (
                    "Sorry, I could not generate an answer right now. "
                    "Please try again in a moment."
                ),
                "sources": sources,
                "is_relevant": retrieval.is_relevant,
                "integrity_flag": integrity_flag,
                "retrieval_scores": retrieval.scores,
                "mode": "error",
            }

        return {
            "answer": answer_text,
            "sources": sources,
            "is_relevant": retrieval.is_relevant,
            "integrity_flag": integrity_flag,
            "retrieval_scores": retrieval.scores,
            "mode": "groq",
        }
