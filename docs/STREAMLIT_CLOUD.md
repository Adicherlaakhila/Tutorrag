# Deploy TutorRAG on Streamlit Community Cloud

Cursor Apps hosting does **not** support Streamlit’s required WebSocket
(`/_stcore/stream`), so the UI stays on a loading skeleton there.

**Use Streamlit Community Cloud** (or another host with long-lived WebSockets).

## 1. Prerequisites

- This GitHub repo pushed (branch `main` or your feature branch)
- Secrets ready: `GROQ_API_KEY`, `QUIZ_ANSWER_BANK`, `APP_ACCESS_CODE`, `CAPTCHA_PEPPER`

## 2. Create the Cloud app

1. Open [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **New app** → select `Adicherlaakhila/Tutorrag` (or your fork).
3. Branch: `main` (or `cursor/tutorrag-web-app-eb06` until merged).
4. **Main file path:** `streamlit_app.py`  
   (Do **not** set `app.py` — that file is the ASGI entry for other hosts.)
5. Deploy.

`runtime.txt` pins Python 3.12. `requirements.txt` installs deps, including the
local `vendor/pyarrow` stub used to keep installs lean.

## 3. Secrets

App settings → **Secrets** (TOML). Example: `.streamlit/secrets.toml.example`.

Required for full AI tutoring:

```toml
GROQ_API_KEY = "..."
QUIZ_ANSWER_BANK = "{\"Q01\":{\"correct_answer\":\"A\",\"explanation\":\"...\"}}"
APP_ACCESS_CODE = "..."
CAPTCHA_PEPPER = "..."
```

Without `GROQ_API_KEY`, chat still works via notes fallback. Without
`CAPTCHA_PEPPER`, the Groq path stays disabled by design.

## 4. Smoke check

1. Open the `*.streamlit.app` URL.
2. Unlock with the class access code.
3. Save a learner profile.
4. Ask a Light / reflection question (solve the CAPTCHA if Groq is configured).
5. Generate a practice quiz.

## 5. Local parity

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
