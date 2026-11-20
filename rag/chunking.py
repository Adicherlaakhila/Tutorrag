"""Split course notes into retrieval-ready chunks."""

from __future__ import annotations

from typing import Any


def notes_to_chunks(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert each note into one or more searchable chunks.

    Short Class 10 notes are kept as single chunks so citations stay aligned
    with note title and section. Longer notes are split by sentence groups.
    """
    chunks: list[dict[str, Any]] = []
    for note in notes:
        pieces = _split_content(note["content"])
        for part_index, text in enumerate(pieces):
            chunks.append(
                {
                    "chunk_id": f"{note['note_id']}-{part_index + 1}",
                    "note_id": note["note_id"],
                    "title": note["title"],
                    "topic_tag": note["topic_tag"],
                    "section": note["section"],
                    "content": text,
                    "citation": f"{note['title']} – Section {note['section']}",
                }
            )
    return chunks


def _split_content(content: str, max_chars: int = 700) -> list[str]:
    content = " ".join(content.split())
    if len(content) <= max_chars:
        return [content]

    sentences = [s.strip() for s in content.replace("?", ".").split(".") if s.strip()]
    if not sentences:
        return [content]

    groups: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        candidate = sentence if sentence.endswith(".") else f"{sentence}."
        extra = len(candidate) + (1 if current else 0)
        if current and current_len + extra > max_chars:
            groups.append(" ".join(current))
            current = [candidate]
            current_len = len(candidate)
        else:
            current.append(candidate)
            current_len += extra
    if current:
        groups.append(" ".join(current))
    return groups
