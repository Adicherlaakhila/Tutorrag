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

- Python + Streamlit
- Groq chat model (`llama-3.3-70b-versatile` by default)
- scikit-learn TF-IDF retrieval
- Local JSON notes + CSV question bank

## Project structure

```text
TutorRAG/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── knowledge_base/notes.json
├── data/question_bank.csv
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
# Edit .env and set GROQ_API_KEY=your_key
streamlit run app.py
```

Open the local URL shown by Streamlit (usually `http://localhost:8501`).

## Streamlit Community Cloud deployment

1. Push this repository to GitHub.
2. Go to [Share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**.
4. Select this repository, branch `main` (or your feature branch), and main file `app.py`.
5. Under **Advanced settings → Secrets**, add:

```toml
GROQ_API_KEY = "your_groq_api_key"
GROQ_MODEL = "llama-3.3-70b-versatile"
```

6. Deploy and open the public URL (no login required for end users).

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
