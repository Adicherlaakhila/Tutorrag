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
├── streamlit_app.py         # Streamlit UI (profile, tutor, quiz)
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── knowledge_base/notes.json
├── data/questions.csv
├── private/                 # local-only; gitignored (not shipped)
├── rag/
│   ├── loader.py
│   ├── chunking.py
│   ├── retrieval.py
│   └── tutor.py
├── utils/
│   ├── prompts.py
│   ├── validation.py
│   └── quiz.py
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

## Streamlit Community Cloud deployment

1. Push this repository to GitHub.
2. Go to [Share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**.
4. Select this repository, branch `main` (or your feature branch), and main file `streamlit_app.py` (or deploy via Cursor using ASGI `app:app`).
5. Under **Advanced settings → Secrets**, add:

```toml
GROQ_API_KEY = "your_groq_api_key"
GROQ_MODEL = "llama-3.3-70b-versatile"
QUIZ_ANSWER_BANK = "{\"Q01\":{\"correct_answer\":\"A\",\"explanation\":\"...\"}}"
APP_ACCESS_CODE = "your-class-access-code"
GROQ_DAILY_LIMIT = "40"
GROQ_MONTHLY_LIMIT = "400"
```

See also `docs/QUIZ_ANSWER_BANK.md`.

6. Deploy and open the public URL. Learners unlock with the class access code, then use a short security check before AI answers.

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
