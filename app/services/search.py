"""
Smart Notes Assistant - Search Retrieval Service
Provides Keyword Search and TF-IDF Cosine Similarity Search over notes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings

STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "is", "are", "was", "were", "my", "our", "your", "this", "that",
    "these", "those", "when", "what", "where", "how", "it", "its", "me", "i", "we"
}


def tokenize(text: str) -> List[str]:
    return re.findall(r"(?u)\b\w+\b|[₹$€£]", text.lower())


class SearchService:
    @staticmethod
    def keyword_search(
        query: str,
        notes: List[Dict[str, Any]],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Exact token frequency and keyword overlap retrieval."""
        q_tokens = [t for t in tokenize(query) if t not in STOPWORDS]
        if not q_tokens:
            q_tokens = tokenize(query)

        if not q_tokens or not notes:
            return []

        scored = []
        for note in notes:
            n_tokens = tokenize(note.get("text", ""))
            # Calculate match count
            match_count = sum(n_tokens.count(tok) for tok in q_tokens)
            if match_count > 0:
                item = dict(note)
                item["score"] = float(match_count)
                scored.append(item)

        scored.sort(key=lambda x: (x["score"], x.get("created_at", "")), reverse=True)
        return scored[:top_k]

    @staticmethod
    def tfidf_search(
        query: str,
        notes: List[Dict[str, Any]],
        top_k: int = 20,
        min_similarity: float = settings.MIN_SEARCH_SIMILARITY
    ) -> List[Dict[str, Any]]:
        """TF-IDF Vector Space Cosine Similarity retrieval."""
        if not notes or not query.strip():
            return []

        texts = [n.get("text", "") for n in notes]
        try:
            vectorizer = TfidfVectorizer(
                token_pattern=r"(?u)\b\w+\b|[₹$€£]",
                stop_words=None,
                sublinear_tf=True
            )
            matrix = vectorizer.fit_transform(texts)
            q_vec = vectorizer.transform([query])
            sims = cosine_similarity(q_vec, matrix)[0]

            ranked_indices = np.argsort(sims)[::-1]
            results = []
            for idx in ranked_indices:
                sim = float(sims[idx])
                if sim >= min_similarity:
                    item = dict(notes[idx])
                    item["score"] = round(sim, 4)
                    results.append(item)
                if len(results) >= top_k:
                    break
            return results
        except Exception:
            # Fallback to keyword search if vectorizer cannot fit (e.g. empty corpus)
            return SearchService.keyword_search(query, notes, top_k)


search_service = SearchService()

