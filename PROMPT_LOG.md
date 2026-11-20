# TutorRAG Prompt Log

| Prompt No. | What the prompt changed |
|---|---|
| 1 | Created the complete TutorRAG application from the full project brief: project structure, 15 course notes, 45-question CSV bank, TF-IDF RAG pipeline, Groq tutor integration with notes fallback, learner profile validation, doubt chat, practice quiz, academic integrity handling, Streamlit UI, automated tests, screenshots, and documentation |
| 2 | Fixed publish security review findings: Groq rate limiting, privacy notice and nickname redaction, encrypted server-side quiz answers, and user-friendly error messages |
| 3 | Hardened remaining publish blockers: moved quiz answers to host-only QUIZ_ANSWER_BANK secret, removed shipped ciphertext/pepper, added IP+session Groq rate limits with request spacing and chat validation |
| 4 | Added class access-code auth, math CAPTCHA, persistent daily/monthly Groq budgets, quiz scrape limits, safer quiz feedback, and production-only answer loading |
