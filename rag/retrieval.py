"""Lightweight TF-IDF retrieval over course note chunks (no scikit-learn)."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any


# Scores below this suggest the query is likely outside the knowledge base.
DEFAULT_RELEVANCE_THRESHOLD = 0.12

# sklearn ENGLISH_STOP_WORDS (kept for retrieval parity with the prior TF-IDF setup).
_ENGLISH_STOP_WORDS = frozenset(
    {
        "a",
        "about",
        "above",
        "across",
        "after",
        "afterwards",
        "again",
        "against",
        "all",
        "almost",
        "alone",
        "along",
        "already",
        "also",
        "although",
        "always",
        "am",
        "among",
        "amongst",
        "amoungst",
        "amount",
        "an",
        "and",
        "another",
        "any",
        "anyhow",
        "anyone",
        "anything",
        "anyway",
        "anywhere",
        "are",
        "around",
        "as",
        "at",
        "back",
        "be",
        "became",
        "because",
        "become",
        "becomes",
        "becoming",
        "been",
        "before",
        "beforehand",
        "behind",
        "being",
        "below",
        "beside",
        "besides",
        "between",
        "beyond",
        "bill",
        "both",
        "bottom",
        "but",
        "by",
        "call",
        "can",
        "cannot",
        "cant",
        "co",
        "con",
        "could",
        "couldnt",
        "cry",
        "de",
        "describe",
        "detail",
        "do",
        "done",
        "down",
        "due",
        "during",
        "each",
        "eg",
        "eight",
        "either",
        "eleven",
        "else",
        "elsewhere",
        "empty",
        "enough",
        "etc",
        "even",
        "ever",
        "every",
        "everyone",
        "everything",
        "everywhere",
        "except",
        "few",
        "fifteen",
        "fifty",
        "fill",
        "find",
        "fire",
        "first",
        "five",
        "for",
        "former",
        "formerly",
        "forty",
        "found",
        "four",
        "from",
        "front",
        "full",
        "further",
        "get",
        "give",
        "go",
        "had",
        "has",
        "hasnt",
        "have",
        "he",
        "hence",
        "her",
        "here",
        "hereafter",
        "hereby",
        "herein",
        "hereupon",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "however",
        "hundred",
        "i",
        "ie",
        "if",
        "in",
        "inc",
        "indeed",
        "interest",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "keep",
        "last",
        "latter",
        "latterly",
        "least",
        "less",
        "ltd",
        "made",
        "many",
        "may",
        "me",
        "meanwhile",
        "might",
        "mill",
        "mine",
        "more",
        "moreover",
        "most",
        "mostly",
        "move",
        "much",
        "must",
        "my",
        "myself",
        "name",
        "namely",
        "neither",
        "never",
        "nevertheless",
        "next",
        "nine",
        "no",
        "nobody",
        "none",
        "noone",
        "nor",
        "not",
        "nothing",
        "now",
        "nowhere",
        "of",
        "off",
        "often",
        "on",
        "once",
        "one",
        "only",
        "onto",
        "or",
        "other",
        "others",
        "otherwise",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "part",
        "per",
        "perhaps",
        "please",
        "put",
        "rather",
        "re",
        "same",
        "see",
        "seem",
        "seemed",
        "seeming",
        "seems",
        "serious",
        "several",
        "she",
        "should",
        "show",
        "side",
        "since",
        "sincere",
        "six",
        "sixty",
        "so",
        "some",
        "somehow",
        "someone",
        "something",
        "sometime",
        "sometimes",
        "somewhere",
        "still",
        "such",
        "system",
        "take",
        "ten",
        "than",
        "that",
        "the",
        "their",
        "them",
        "themselves",
        "then",
        "thence",
        "there",
        "thereafter",
        "thereby",
        "therefore",
        "therein",
        "thereupon",
        "these",
        "they",
        "thick",
        "thin",
        "third",
        "this",
        "those",
        "though",
        "three",
        "through",
        "throughout",
        "thru",
        "thus",
        "to",
        "together",
        "too",
        "top",
        "toward",
        "towards",
        "twelve",
        "twenty",
        "two",
        "un",
        "under",
        "until",
        "up",
        "upon",
        "us",
        "very",
        "via",
        "was",
        "we",
        "well",
        "were",
        "what",
        "whatever",
        "when",
        "whence",
        "whenever",
        "where",
        "whereafter",
        "whereas",
        "whereby",
        "wherein",
        "whereupon",
        "wherever",
        "whether",
        "which",
        "while",
        "whither",
        "who",
        "whoever",
        "whole",
        "whom",
        "whose",
        "why",
        "will",
        "with",
        "within",
        "without",
        "would",
        "yet",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
    }
)

# Matches sklearn TfidfVectorizer default token_pattern (?u)\b\w\w+\b
_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens with English stop-word filtering and 1–2 grams."""
    unigrams = [
        tok
        for tok in _TOKEN_RE.findall((text or "").lower())
        if tok not in _ENGLISH_STOP_WORDS
    ]
    if not unigrams:
        return []
    bigrams = [f"{unigrams[i]} {unigrams[i + 1]}" for i in range(len(unigrams) - 1)]
    return unigrams + bigrams


def _l2_normalize(weights: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in weights.values()))
    if norm <= 0.0:
        return weights
    return {term: value / norm for term, value in weights.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


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

        tokenized = [_tokenize(doc) for doc in self.documents]
        doc_count = len(tokenized)
        document_frequency: Counter[str] = Counter()
        for tokens in tokenized:
            document_frequency.update(set(tokens))

        # sklearn smooth_idf: idf(t) = log((1 + n) / (1 + df(t))) + 1
        self._idf = {
            term: math.log((1.0 + doc_count) / (1.0 + df)) + 1.0
            for term, df in document_frequency.items()
        }

        self._vectors: list[dict[str, float]] = []
        for tokens in tokenized:
            tf = Counter(tokens)
            weights = {
                term: float(count) * self._idf[term] for term, count in tf.items()
            }
            self._vectors.append(_l2_normalize(weights))

    def _vectorize_query(self, query: str) -> dict[str, float]:
        tokens = _tokenize(query)
        if not tokens:
            return {}
        tf = Counter(tokens)
        weights = {
            term: float(count) * self._idf[term]
            for term, count in tf.items()
            if term in self._idf
        }
        return _l2_normalize(weights)

    def retrieve(self, query: str, top_k: int = 3) -> RetrievalResult:
        query = (query or "").strip()
        if not query:
            return RetrievalResult(chunks=[], scores=[], max_score=0.0, is_relevant=False)

        query_vec = self._vectorize_query(query)
        if not query_vec:
            return RetrievalResult(chunks=[], scores=[], max_score=0.0, is_relevant=False)

        similarities = [_cosine(query_vec, doc_vec) for doc_vec in self._vectors]
        ranked_indices = sorted(
            range(len(similarities)),
            key=lambda index: similarities[index],
            reverse=True,
        )[:top_k]

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
            chunks=selected_chunks,
            scores=selected_scores,
            max_score=max_score,
            is_relevant=is_relevant,
        )
