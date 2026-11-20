"""TF-IDF retrieval over course note chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Scores below this suggest the query is likely outside the knowledge base.
DEFAULT_RELEVANCE_THRESHOLD = 0.12


@dataclass
class RetrievalResult:
    chunks: list[dict[str, Any]]
    scores: list[float]
    max_score: float
    is_relevant: bool


class TFIDFRetriever:
    """Retrieve the top-k most relevant note chunks for a student question."""

    def __init__(
        self,
        chunks: list[dict[str, Any]],
        relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> None:
        if not chunks:
            raise ValueError("Cannot build retriever with an empty chunk list.")
        self.chunks = chunks
        self.relevance_threshold = relevance_threshold
        self.documents = [
            f"{chunk['title']} {chunk['topic_tag']} Section {chunk['section']} {chunk['content']}"
            for chunk in chunks
        ]
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        self.matrix = self.vectorizer.fit_transform(self.documents)

    def retrieve(self, query: str, top_k: int = 3) -> RetrievalResult:
        query = (query or "").strip()
        if not query:
            return RetrievalResult(chunks=[], scores=[], max_score=0.0, is_relevant=False)

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.matrix).flatten()
        ranked_indices = similarities.argsort()[::-1][:top_k]

        selected_chunks: list[dict[str, Any]] = []
        selected_scores: list[float] = []
        for index in ranked_indices:
            score = float(similarities[index])
            if score <= 0:
                continue
            chunk = dict(self.chunks[int(index)])
            chunk["score"] = round(score, 4)
            selected_chunks.append(chunk)
            selected_scores.append(score)

        max_score = max(selected_scores) if selected_scores else 0.0
        is_relevant = bool(selected_chunks) and max_score >= self.relevance_threshold
        return RetrievalResult(
            chunks=selected_chunks if is_relevant else selected_chunks,
            scores=selected_scores,
            max_score=max_score,
            is_relevant=is_relevant,
        )
