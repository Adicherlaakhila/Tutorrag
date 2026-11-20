# TutorRAG Test Note

Three questions were tested against the running app and automated suite.

**1. “What is reflection of light?” (Beginner)**  
Expected: a simple explanation grounded in course notes with real citations.  
Actual: TF-IDF retrieved *Reflection of Light – Section 1.2* (and related notes). The beginner answer used simple wording and cited those sources.

**2. Same question for an Advanced learner**  
Expected: deeper, exam-oriented detail with citations from the same notes.  
Actual: retrieval matched the same note set; the advanced answer was longer and more exam-focused than the beginner response.

**3. “Explain human digestion…” (out of syllabus)**  
Expected: refuse fabrication and invite a Light-unit question.  
Actual: relevance stayed below threshold; the chat said the question is outside the available syllabus notes.

Additional checks passed for incomplete profiles, quiz scoring with explanations, and homework integrity (hints/steps only, not a submit-ready answer).

**Limitation:** Full Groq LLM wording requires `GROQ_API_KEY` in `.env` or Streamlit Secrets. Without it, answers still come from retrieved notes with citations via the notes-grounded fallback.
