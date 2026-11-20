"""TutorRAG – Class 10 Science AI tutoring app (Streamlit)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import streamlit as st

from rag.tutor import TutorService
from utils.auth_gate import auth_required, verify_access_code
from utils.captcha import issue_math_captcha
from utils.client_identity import resolve_client_bucket
from utils.quiz import (
    available_topics,
    grade_quiz,
    load_question_bank,
    select_quiz_questions,
)
from utils.rate_limit import (
    ACCESS_CODE_RATE_LIMITER,
    QUIZ_RATE_LIMITER,
    QUIZ_SUBMIT_RATE_LIMITER,
)
from utils.validation import (
    DEFAULT_SUBJECT,
    DEFAULT_TOPIC,
    VALID_LEVELS,
    VALID_STYLES,
    profile_summary,
    validate_profile,
)

logger = logging.getLogger(__name__)

ACADEMIC_INTEGRITY_NOTICE = (
    "TutorRAG is designed to help you learn. It provides explanations, hints, "
    "and guided steps. It does not complete graded assignments or write work for submission."
)

PRIVACY_NOTICE = (
    "Privacy: When AI chat is available, your question, recent chat turns, and "
    "non-identifying learning preferences (level, subject, topic, style) may be "
    "sent to Groq’s third-party AI service to generate a reply. Your nickname is "
    "not sent to Groq. Do not enter passwords, personal contact details, or "
    "other sensitive information in chat. Quiz answers are checked on the server "
    "and are never included in downloadable question files. API keys stay on the server."
)


def _init_state() -> None:
    defaults = {
        "profile": None,
        "profile_edit_mode": True,
        "messages": [],
        "quiz_questions": None,
        "quiz_submitted": False,
        "quiz_result": None,
        "quiz_error": None,
        "tutor": None,
        "question_bank": None,
        "client_key": None,
        "authenticated": False,
        "captcha_prompt": None,
        "captcha_token": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not st.session_state.client_key:
        st.session_state.client_key = f"session-{uuid.uuid4().hex}"
    # Local/dev without APP_ACCESS_CODE remains usable.
    if not auth_required():
        st.session_state.authenticated = True
    if not st.session_state.captcha_token:
        challenge = issue_math_captcha()
        st.session_state.captcha_prompt = challenge.prompt
        st.session_state.captcha_token = challenge.token


def _refresh_captcha() -> None:
    challenge = issue_math_captcha()
    st.session_state.captcha_prompt = challenge.prompt
    st.session_state.captcha_token = challenge.token


@st.cache_resource
def get_tutor_service() -> TutorService:
    return TutorService()


@st.cache_data
def get_question_bank():
    return load_question_bank()


def render_integrity_banner() -> None:
    st.info(f"📚 Academic Integrity: {ACADEMIC_INTEGRITY_NOTICE}")


def render_privacy_banner() -> None:
    st.caption(PRIVACY_NOTICE)


def render_access_gate() -> bool:
    """Return True when the learner is allowed to use protected features."""
    if st.session_state.authenticated:
        return True
    st.warning("Enter the class access code to unlock TutorRAG.")
    with st.form("access_code_form"):
        code = st.text_input("Class access code *", type="password")
        submitted = st.form_submit_button("Unlock", use_container_width=True)
    if submitted:
        allowed, limit_message = ACCESS_CODE_RATE_LIMITER.allow(
            ip_key=resolve_client_bucket(),
            session_key=st.session_state.client_key,
        )
        if not allowed:
            st.error(limit_message or "Too many unlock attempts. Please wait.")
            return False
        if verify_access_code(code):
            st.session_state.authenticated = True
            st.success("Access unlocked for this session.")
            st.rerun()
        st.error("That access code is not valid.")
    return False


def render_profile_form(sidebar: bool = False) -> None:
    container = st.sidebar if sidebar else st
    profile = st.session_state.profile or {}

    container.subheader("Learner Profile")
    with container.form("learner_profile_form", clear_on_submit=False):
        nickname = st.text_input(
            "Nickname *",
            value=profile.get("nickname", ""),
            placeholder="e.g. Alex",
        )
        level = st.selectbox(
            "Learning level *",
            options=list(VALID_LEVELS),
            index=list(VALID_LEVELS).index(profile["level"])
            if profile.get("level") in VALID_LEVELS
            else 0,
        )
        subject = st.text_input(
            "Subject *",
            value=profile.get("subject", DEFAULT_SUBJECT),
        )
        topic = st.text_input(
            "Current topic *",
            value=profile.get("topic", DEFAULT_TOPIC),
        )
        style = st.selectbox(
            "Preferred explanation style *",
            options=list(VALID_STYLES),
            index=list(VALID_STYLES).index(profile["style"])
            if profile.get("style") in VALID_STYLES
            else 0,
        )
        submitted = st.form_submit_button(
            "Save profile" if not profile else "Update profile",
            use_container_width=True,
        )

    if submitted:
        ok, errors, cleaned = validate_profile(nickname, level, subject, topic, style)
        if not ok:
            for err in errors:
                container.error(err)
        else:
            st.session_state.profile = cleaned
            st.session_state.profile_edit_mode = False
            container.success(f"Profile saved for {cleaned['nickname']}.")
            st.rerun()


def render_sidebar() -> None:
    st.sidebar.markdown("## 🎓 TutorRAG")
    st.sidebar.caption("Class 10 Science · Light")
    st.sidebar.divider()

    if st.session_state.authenticated:
        st.sidebar.caption("Access: unlocked")
    elif auth_required():
        st.sidebar.caption("Access: locked")

    profile = st.session_state.profile
    if profile and not st.session_state.profile_edit_mode:
        st.sidebar.markdown("**Learner**")
        st.sidebar.write(f"👤 {profile['nickname']}")
        st.sidebar.write(f"📘 Subject: {profile['subject']}")
        st.sidebar.write(f"🧩 Topic: {profile['topic']}")
        st.sidebar.write(f"📶 Level: {profile['level']}")
        st.sidebar.write(f"✍️ Style: {profile['style']}")
        if st.sidebar.button("Update profile", use_container_width=True):
            st.session_state.profile_edit_mode = True
            st.rerun()
    else:
        render_profile_form(sidebar=True)

    st.sidebar.divider()
    if st.sidebar.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.sidebar.success("Chat cleared.")
        st.rerun()


def render_chat() -> None:
    st.subheader("AI Doubt Chat")
    st.caption("Ask a Science doubt about Light – Reflection and Refraction.")

    if not st.session_state.authenticated:
        st.warning("Unlock TutorRAG with the class access code to use AI chat.")
        return

    profile = st.session_state.profile
    if not profile:
        st.warning("Please complete your learner profile in the sidebar before chatting.")
        return

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                st.markdown("**Sources used**")
                for source in message["sources"]:
                    st.markdown(f"- {source['label']}")

    with st.expander("Security check (required for AI answers)", expanded=True):
        st.caption(st.session_state.captcha_prompt or "Loading security check…")
        captcha_answer = st.text_input(
            "Your answer",
            key="captcha_answer_input",
            label_visibility="collapsed",
            placeholder="Type the number",
        )
        if st.button("New security question", key="refresh_captcha"):
            _refresh_captcha()
            st.rerun()

    prompt = st.chat_input("Type your Science doubt here…")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving notes and thinking…"):
            try:
                tutor = get_tutor_service()
                result = tutor.answer(
                    question=prompt,
                    profile=profile,
                    history=st.session_state.messages[:-1],
                    client_key=st.session_state.client_key,
                    client_ip=resolve_client_bucket(),
                    captcha_token=st.session_state.captcha_token,
                    captcha_answer=captcha_answer,
                    authenticated=bool(st.session_state.authenticated),
                )
            except Exception:
                logger.exception("Chat answer failed")
                st.error(
                    "Sorry, I could not generate an answer right now. Please try again."
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "Sorry, I could not generate an answer right now. "
                            "Please try again in a moment."
                        ),
                        "sources": [],
                    }
                )
                _refresh_captcha()
                return

            st.markdown(result["answer"])
            if result["sources"]:
                st.markdown("**Sources used**")
                for source in result["sources"]:
                    st.markdown(f"- {source['label']}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
        }
    )
    # One-time CAPTCHA token: refresh after every AI attempt.
    _refresh_captcha()


def render_quiz() -> None:
    st.subheader("Practice Quiz")
    st.caption("Five questions filtered by topic and learning level.")

    if not st.session_state.authenticated:
        st.warning("Unlock TutorRAG with the class access code to use the practice quiz.")
        return

    profile = st.session_state.profile
    if not profile:
        st.warning("Save your learner profile to generate a matched practice quiz.")
        return

    try:
        bank = get_question_bank()
    except Exception:
        logger.exception("Question bank load failed")
        st.error("Could not load the practice quiz right now. Please try again later.")
        return

    topics = ["(All topics in unit)"] + available_topics(bank)
    default_topic = profile.get("topic", DEFAULT_TOPIC)
    topic_index = 0
    for idx, topic_name in enumerate(topics):
        if topic_name.casefold() == str(default_topic).casefold():
            topic_index = idx
            break

    col1, col2 = st.columns(2)
    with col1:
        selected_topic = st.selectbox("Quiz topic", options=topics, index=topic_index)
    with col2:
        selected_level = st.selectbox(
            "Quiz difficulty",
            options=list(VALID_LEVELS),
            index=list(VALID_LEVELS).index(profile["level"])
            if profile.get("level") in VALID_LEVELS
            else 0,
        )

    topic_filter = None if selected_topic.startswith("(All") else selected_topic

    if st.button("Generate 5-question quiz", use_container_width=True):
        allowed, limit_message = QUIZ_RATE_LIMITER.allow(
            ip_key=resolve_client_bucket(),
            session_key=st.session_state.client_key,
        )
        if not allowed:
            st.session_state.quiz_error = limit_message
            st.session_state.quiz_questions = None
            st.rerun()
        questions, error = select_quiz_questions(
            bank,
            topic=topic_filter,
            difficulty=selected_level,
            count=5,
        )
        st.session_state.quiz_questions = questions
        st.session_state.quiz_error = error
        st.session_state.quiz_submitted = False
        st.session_state.quiz_result = None
        st.rerun()

    if st.session_state.quiz_error:
        st.warning(st.session_state.quiz_error)

    questions = st.session_state.quiz_questions
    if not questions:
        return

    with st.form("quiz_form"):
        answers: dict[str, str] = {}
        for index, question in enumerate(questions, start=1):
            st.markdown(f"**Q{index}. {question['question']}**")
            st.caption(f"{question['topic']} · {question['difficulty']}")
            option_labels = [
                f"{key}. {value}" for key, value in question["options"].items()
            ]
            choice = st.radio(
                f"Answer for question {index}",
                options=option_labels,
                key=f"quiz_choice_{question['question_id']}",
                label_visibility="collapsed",
            )
            answers[question["question_id"]] = choice.split(".", 1)[0].strip()
            st.divider()

        submitted = st.form_submit_button("Submit quiz", use_container_width=True)

    if submitted:
        allowed, limit_message = QUIZ_SUBMIT_RATE_LIMITER.allow(
            ip_key=resolve_client_bucket(),
            session_key=st.session_state.client_key,
        )
        if not allowed:
            st.warning(limit_message or "Quiz submit limit reached. Please try later.")
        else:
            graded = grade_quiz(questions, answers)
            # Do not keep correct letters/explanations in session (reduces scrape risk).
            st.session_state.quiz_result = {
                "score": graded["score"],
                "total": graded["total"],
                "details": [
                    {
                        "question_id": item["question_id"],
                        "is_correct": item["is_correct"],
                        "selected": item["selected"],
                    }
                    for item in graded["details"]
                ],
            }
            st.session_state.quiz_submitted = True

    if st.session_state.quiz_submitted and st.session_state.quiz_result:
        result = st.session_state.quiz_result
        st.success(f"Score: {result['score']} / {result['total']}")
        for index, item in enumerate(result["details"], start=1):
            if item["is_correct"]:
                st.markdown(f"✅ **Q{index}** – Correct")
            else:
                selected = item["selected"] or "No answer"
                st.markdown(f"❌ **Q{index}** – Incorrect (Your answer: {selected})")
                # Generic coaching only — avoid answer-key explanations that map to options.
                st.markdown(
                    "Review this topic in your course notes and try a similar question again."
                )


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 920px;}
        h1, h2, h3 {font-family: "Trebuchet MS", "Segoe UI", sans-serif;}
        div[data-testid="stChatMessage"] {border-radius: 12px;}
        @media (max-width: 768px) {
            .block-container {padding-left: 1rem; padding-right: 1rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="TutorRAG – Class 10 Science Tutor",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_state()
    apply_styles()
    render_sidebar()

    st.title("TutorRAG")
    st.markdown(
        "Your Class 10 Science tutor for **Light – Reflection and Refraction**. "
        "Ask doubts, get cited explanations from course notes, and practise with quizzes."
    )
    render_integrity_banner()
    render_privacy_banner()

    if not render_access_gate():
        return

    if st.session_state.profile:
        st.caption(f"Active profile: {profile_summary(st.session_state.profile)}")
    else:
        st.warning("Start by saving your learner profile in the sidebar.")

    tab_chat, tab_quiz, tab_about = st.tabs(
        ["Doubt Chat", "Practice Quiz", "About"]
    )
    with tab_chat:
        render_chat()
    with tab_quiz:
        render_quiz()
    with tab_about:
        st.markdown(
            """
            ### About TutorRAG
            TutorRAG uses Retrieval-Augmented Generation (RAG):
            1. Loads local Class 10 Science notes
            2. Retrieves the top relevant note chunks with TF-IDF
            3. Asks a Groq LLM to explain using those notes and your learning preferences

            ### Privacy
            When AI chat is enabled, questions and learning preferences may be sent to
            **Groq**, a third-party AI provider, to generate answers. Nicknames are not
            sent to Groq. Practice-quiz answer keys are checked on the server and are not
            included in the public question file. API secrets never appear in the browser UI.

            ### Security and usage limits
            - Class access code unlocks the app for a session
            - AI answers require a short security check (CAPTCHA)
            - Groq calls are limited per network/session and by daily/monthly budgets
            - Quiz generation is rate-limited to reduce answer-bank scraping
            """
        )
        notes_path = Path("knowledge_base/notes.json")
        if notes_path.exists():
            st.success("Knowledge base file found.")
        bank_path = Path("data/questions.csv")
        if bank_path.exists():
            st.success("Practice questions file found.")


if __name__ == "__main__":
    main()
