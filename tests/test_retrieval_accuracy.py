"""Retrieval quality and document-processing regression tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag.chunking import notes_to_chunks
from rag.loader import load_notes
from rag.retrieval import TFIDFRetriever, _tokenize


SYLLABUS_CASES = [
    ("What are the laws of reflection?", ("reflection", "law")),
    ("Explain refraction of light through a glass slab.", ("refraction", "glass")),
    ("What is the mirror formula for spherical mirrors?", ("mirror", "formula")),
    ("Define refractive index of a medium.", ("refractive", "index")),
    ("Difference between real and virtual images.", ("real", "virtual")),
]


def _build_retriever() -> TFIDFRetriever:
    notes = load_notes()
    chunks = notes_to_chunks(notes)
    assert chunks, "Expected non-empty chunks from course notes"
    return TFIDFRetriever(chunks)


def test_notes_are_processed_into_chunks_with_citations():
    notes = load_notes()
    chunks = notes_to_chunks(notes)
    assert len(notes) >= 10
    assert len(chunks) >= len(notes)
    for chunk in chunks:
        assert chunk["note_id"]
        assert chunk["title"]
        assert chunk["topic_tag"]
        assert chunk["section"]
        assert chunk["content"]
        assert len(chunk["content"]) > 20


def test_tokenizer_emits_unigrams_and_bigrams_without_stopwords():
    tokens = _tokenize("The laws of reflection of light")
    assert "laws" in tokens
    assert "reflection" in tokens
    assert "the" not in tokens
    assert "of" not in tokens
    assert "laws reflection" in tokens
    assert "reflection light" in tokens


def test_syllabus_queries_retrieve_relevant_titled_chunks():
    retriever = _build_retriever()
    for query, expected_terms in SYLLABUS_CASES:
        result = retriever.retrieve(query, top_k=3)
        assert result.is_relevant, f"Expected relevant hit for: {query}"
        assert 1 <= len(result.chunks) <= 3
        assert result.max_score >= retriever.relevance_threshold
        blob = " ".join(
            f"{chunk['title']} {chunk['topic_tag']} {chunk['content']}".lower()
            for chunk in result.chunks
        )
        assert any(term in blob for term in expected_terms), (
            f"No expected terms {expected_terms} in retrieval for: {query}"
        )


def test_out_of_syllabus_queries_are_not_forced_relevant():
    retriever = _build_retriever()
    queries = [
        "Explain the complete process of human digestion in the stomach.",
        "How do political parties form a coalition government?",
        "Write a poem about monsoon rains in Kerala.",
    ]
    for query in queries:
        result = retriever.retrieve(query, top_k=3)
        assert result.max_score < 0.25 or not result.is_relevant, query


def test_retrieval_ranking_is_stable_for_identical_queries():
    retriever = _build_retriever()
    query = "What is refraction of light?"
    first = retriever.retrieve(query, top_k=3)
    second = retriever.retrieve(query, top_k=3)
    assert [c["note_id"] for c in first.chunks] == [c["note_id"] for c in second.chunks]
    assert first.scores == second.scores


def test_empty_query_returns_no_hits():
    retriever = _build_retriever()
    result = retriever.retrieve("   ", top_k=3)
    assert result.chunks == []
    assert result.max_score == 0.0
    assert result.is_relevant is False
