# TutorRAG

TutorRAG is a working Class 10 Science tutoring web app for the unit **Light – Reflection and Refraction**. It uses Retrieval-Augmented Generation (RAG) with local course notes, TF-IDF retrieval, and the Groq API.

## Features

1. **Learner profile** – nickname, level, subject, topic, explanation style (validated and stored in Streamlit session)
2. **AI doubt chat** – Groq-powered answers adapted to learner level and style
3. **RAG citations** – top-3 TF-IDF note chunks with real source labels
4. **Course knowledge base** – 15 original notes in `knowledge_base/notes.json`
5. **Practice quiz** – 45 CSV questions; generates exactly 5 matched questions with scoring
6. **Academic integrity** – visible notice; homework/assignment requests get hints and guided steps, not ready-to-submit answers

## Tech stack

- Python + Streamlit (ASGI via `st.App`)
- Groq chat model (`llama-3.3-70b-versatile` by default)
- Lightweight pure-Python TF-IDF retrieval (no scikit-learn / SciPy)
- Local JSON notes + CSV question bank via stdlib `csv`
- Deploy-size stub at `vendor/pyarrow` (package name `pyarrow`) so Cursor/`uv` publish stays under the 500 MB limit

## Project structure

```text
TutorRAG/
├── app.py                   # ASGI entry: st.App → streamlit_app.py
├── streamlit_app.py         # Streamlit UI / Streamlit Cloud main file
├── runtime.txt              # Streamlit Cloud Python pin
├── requirements.txt
├── .streamlit/config.toml
├── .streamlit/secrets.toml.example
├── vendor/pyarrow/          # lean pyarrow stub for size-constrained hosts
├── docs/STREAMLIT_CLOUD.md
├── knowledge_base/notes.json
├── data/questions.csv
├── private/                 # local-only; gitignored (not shipped)
├── rag/
├── utils/
├── screenshots/
└── tests/
```

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GROQ_API_KEY / QUIZ_ANSWER_BANK / APP_ACCESS_CODE
# Preferred (ASGI / Cursor publisher entry point):
uvicorn app:app --host 127.0.0.1 --port 8501
# Or classic Streamlit CLI:
streamlit run streamlit_app.py
```

Open the local URL shown by the server (usually `http://localhost:8501`).

Deployment note: `app.py` exports Streamlit’s official ASGI `app = st.App("streamlit_app.py")`. The UI and features remain in `streamlit_app.py`.

Public-host secrets: set `GROQ_API_KEY`, `QUIZ_ANSWER_BANK`, `APP_ACCESS_CODE`, and `CAPTCHA_PEPPER` (required for the Groq AI path across workers). Rate limits and Groq budgets are process-local unless the host shares persistent storage.

## Deployment

**Recommended: Streamlit Community Cloud** (supports Streamlit WebSockets).

Cursor Apps (`*.apps.grok.bot`) can host the build, but Streamlit’s UI WebSocket
(`/_stcore/stream`) is not available there, so the page stays on a loading
skeleton. Prefer Streamlit Cloud for a working classroom link.

Quick path:

1. [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Repo + branch, **Main file:** `streamlit_app.py`
3. Secrets from `.streamlit/secrets.toml.example` (include `CAPTCHA_PEPPER`)

Full steps: [docs/STREAMLIT_CLOUD.md](docs/STREAMLIT_CLOUD.md). Answer-bank format: [docs/QUIZ_ANSWER_BANK.md](docs/QUIZ_ANSWER_BANK.md).

## Tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```

Live Groq tests in `tests/test_groq_live.py` run only when `GROQ_API_KEY` is set.

## Prompt log

See [PROMPT_LOG.md](PROMPT_LOG.md).

## Test note

See [TEST_NOTE.md](TEST_NOTE.md) (actual executed results, 150–200 words).

## Screenshots

Genuine app screenshots are in `screenshots/`:

1. `01_learner_profile_form.png`
2. `02_beginner_answer_with_citations.png`
3. `03_advanced_answer_with_citations.png`
4. `04_practice_quiz_feedback.png`
5. `05_out_of_syllabus_handling.png` / `05b_homework_integrity_handling.png`
6. `06_mobile_responsive_view.png`
