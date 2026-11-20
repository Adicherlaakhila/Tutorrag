"""Load course notes from the local knowledge base."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_NOTES_PATH = Path(__file__).resolve().parent.parent / "knowledge_base" / "notes.json"


def load_notes(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load and validate course notes from a JSON file."""
    notes_path = Path(path) if path else DEFAULT_NOTES_PATH
    if not notes_path.exists():
        raise FileNotFoundError(f"Knowledge base not found: {notes_path}")

    with notes_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list) or not data:
        raise ValueError("Knowledge base must be a non-empty JSON list of notes.")

    required = {"note_id", "title", "topic_tag", "section", "content"}
    validated: list[dict[str, Any]] = []
    for index, note in enumerate(data):
        if not isinstance(note, dict):
            raise ValueError(f"Note at index {index} is not an object.")
        missing = required - set(note.keys())
        if missing:
            raise ValueError(f"Note at index {index} missing fields: {sorted(missing)}")
        validated.append(
            {
                "note_id": str(note["note_id"]).strip(),
                "title": str(note["title"]).strip(),
                "topic_tag": str(note["topic_tag"]).strip(),
                "section": str(note["section"]).strip(),
                "content": str(note["content"]).strip(),
            }
        )
    return validated
