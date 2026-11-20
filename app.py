"""TutorRAG – Class 10 Science AI tutoring app (Streamlit)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from rag.tutor import TutorService
from utils.quiz import (
    available_topics,
    grade_quiz,
    load_question_bank,
    select_quiz_questions,
)
from utils.validation import (
    DEFAULT_SUBJECT,
    DEFAULT_TOPIC,
    VALID_LEVELS,
    VALID_STYLES,
    profile_summary,
    validate_profile,
)


ACADEMIC_INTEGRITY_NOTICE = (
    "TutorRAG is designed to help you learn. It provides explanations, hints, "
    "and guided steps. It does not complete graded assignments or write work for submission."
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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource
def get_tutor_service() -> TutorService:
    return TutorService()


@st.cache_data
def get_question_bank():
    return load_question_bank()


def render_integrity_banner() -> None:
    st.info(f"📚 Academic Integrity: {ACADEMIC_INTEGRITY_NOTICE}")


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
                )
            except Exception as exc:  # noqa: BLE001 - show friendly UI error
                st.error(f"Could not generate an answer: {exc}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "Sorry, I could not reach the tutoring service. "
                            "Please check that GROQ_API_KEY is configured and try again."
                        ),
                        "sources": [],
                    }
                )
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


def render_quiz() -> None:
    st.subheader("Practice Quiz")
    st.caption("Five questions filtered by topic and learning level.")

    profile = st.session_state.profile
    if not profile:
        st.warning("Save your learner profile to generate a matched practice quiz.")
        return

    try:
        bank = get_question_bank()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load question bank: {exc}")
        return

    topics = ["(All topics in unit)"] + available_topics(bank)
    default_topic = profile.get("topic", DEFAULT_TOPIC)
    # Map broad unit topic to "all topics" filter by default.
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
            st.caption(
                f"{question['topic']} · {question['difficulty']} · {question['question_id']}"
            )
            option_labels = [
                f"{key}. {value}" for key, value in question["options"].items()
            ]
            choice = st.radio(
                f"Answer for {question['question_id']}",
                options=option_labels,
                key=f"quiz_choice_{question['question_id']}",
                label_visibility="collapsed",
            )
            answers[question["question_id"]] = choice.split(".", 1)[0].strip()
            st.divider()

        submitted = st.form_submit_button("Submit quiz", use_container_width=True)

    if submitted:
        st.session_state.quiz_result = grade_quiz(questions, answers)
        st.session_state.quiz_submitted = True

    if st.session_state.quiz_submitted and st.session_state.quiz_result:
        result = st.session_state.quiz_result
        st.success(f"Score: {result['score']} / {result['total']}")
        for item in result["details"]:
            if item["is_correct"]:
                st.markdown(
                    f"✅ **{item['question_id']}** – Correct "
                    f"(Answer: {item['correct_answer']})"
                )
            else:
                selected = item["selected"] or "No answer"
                st.markdown(
                    f"❌ **{item['question_id']}** – Incorrect "
                    f"(Your answer: {selected}; Correct: {item['correct_answer']})"
                )
                st.markdown(f"Explanation: {item['explanation']}")


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
            3. Asks a Groq LLM to explain using those notes and your learner profile

            Knowledge base folder: `knowledge_base/`  
            Question bank: `data/question_bank.csv`
            """
        )
        notes_path = Path("knowledge_base/notes.json")
        if notes_path.exists():
            st.success("Knowledge base file found.")
        bank_path = Path("data/question_bank.csv")
        if bank_path.exists():
            st.success("Question bank file found.")


if __name__ == "__main__":
    main()
