# `QUIZ_ANSWER_BANK` secret format

## What it is

`QUIZ_ANSWER_BANK` is the **actual quiz answer bank as JSON**.

It is **not** an encryption key, API key, or password.

## Why this design

- Public file `data/questions.csv` contains only question text and options.
- Correct answers and explanations are **never** stored in that CSV.
- Production grading reads answers only from the host secret `QUIZ_ANSWER_BANK`
  (environment variable or Streamlit/Cursor secrets).
- Local development may use gitignored `private/answers.dev.json` as a fallback.
  That file is not committed and must not be shipped.

## Exact JSON schema

Top-level object keyed by `question_id`.

Each value must include:

| Field | Type | Allowed values |
|---|---|---|
| `correct_answer` | string | `A`, `B`, `C`, or `D` |
| `explanation` | string | short explanation shown after quiz submit |

### Minimal example

```json
{
  "Q01": {
    "correct_answer": "A",
    "explanation": "Light is a form of energy that enables us to see objects."
  },
  "Q02": {
    "correct_answer": "A",
    "explanation": "The speed of light in vacuum is about 3 × 10^8 metres per second."
  }
}
```

### Cursor / env secret value

Paste the JSON as **one string** (single line is fine):

```text
{"Q01":{"correct_answer":"A","explanation":"Light is a form of energy that enables us to see objects."},"Q02":{"correct_answer":"A","explanation":"The speed of light in vacuum is about 3 × 10^8 metres per second."}}
```

### Streamlit `secrets.toml` options

Either a JSON string:

```toml
QUIZ_ANSWER_BANK = "{\"Q01\":{\"correct_answer\":\"A\",\"explanation\":\"...\"}}"
```

or a native table (also supported by the loader):

```toml
[QUIZ_ANSWER_BANK.Q01]
correct_answer = "A"
explanation = "Light is a form of energy that enables us to see objects."
```

## Runtime retrieval order

1. `QUIZ_ANSWER_BANK` host secret / environment variable (production)
2. gitignored `private/answers.dev.json` (local only)
3. otherwise empty → quiz generation/grading cannot use real answers

Answers are used only inside server-side `grade_quiz()` after submit.
They are never written into the public question CSV or returned before submission.
