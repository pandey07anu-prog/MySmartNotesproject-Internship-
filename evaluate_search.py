"""
Smart Notes Assistant - Search Retrieval Evaluation & Benchmarking
Evaluates Keyword Search vs TF-IDF Cosine Similarity Search on the official
starter notes (data/starter_notes.json) using the 15 benchmark queries (data/search_queries.json).
Calculates Hit Rate @ 3 and reports failed queries.

Usage:
    python evaluate_search.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "is", "are", "was", "were", "my", "our", "your", "this", "that",
    "these", "those", "when", "what", "where", "how", "it", "its", "me", "i", "we"
}


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric and currency tokens."""
    return re.findall(r"(?u)\b\w+\b|[₹$€£]", text.lower())


def content_tokens(text: str) -> Set[str]:
    """Extract non-stopword, non-numeric tokens."""
    return {t for t in tokenize(text) if t not in STOPWORDS and not t.isdigit()}


def keyword_search(query: str, corpus: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """Simple term-frequency matching baseline."""
    q_tokens = [t for t in tokenize(query) if t not in STOPWORDS]
    if not q_tokens:
        q_tokens = tokenize(query)

    scored = []
    for note in corpus:
        note_tokens = tokenize(note["text"])
        # Count token occurrences
        score = sum(note_tokens.count(tok) for tok in q_tokens)
        if score > 0:
            scored.append({
                "note_id": note["id"],
                "text": note["text"],
                "score": score
            })

    # Sort descending by score, tie-break by note_id
    scored.sort(key=lambda x: (x["score"], -int(re.sub(r"\D", "", x["note_id"] or "0"))), reverse=True)
    return scored[:top_k]


def tfidf_search(
    query: str,
    corpus: List[Dict[str, Any]],
    vectorizer: TfidfVectorizer,
    matrix: np.ndarray,
    top_k: int = 3,
    min_similarity: float = 0.05
) -> List[Dict[str, Any]]:
    """TF-IDF Cosine Similarity Search."""
    q_vec = vectorizer.transform([query])
    sims = cosine_similarity(q_vec, matrix)[0]
    ranked_indices = np.argsort(sims)[::-1]

    results = []
    for idx in ranked_indices:
        sim = float(sims[idx])
        if sim >= min_similarity:
            results.append({
                "note_id": corpus[idx]["id"],
                "text": corpus[idx]["text"],
                "score": round(sim, 4)
            })
        if len(results) >= top_k:
            break
    return results


def run_evaluation() -> Dict[str, Any]:
    notes_path = DATA_DIR / "starter_notes.json"
    queries_path = DATA_DIR / "search_queries.json"

    with open(notes_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    with open(queries_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    # Fit TF-IDF Vectorizer
    corpus_texts = [n["text"] for n in corpus]
    vectorizer = TfidfVectorizer(
        token_pattern=r"(?u)\b\w+\b|[₹$€£]",
        stop_words=None,
        sublinear_tf=True
    )
    matrix = vectorizer.fit_transform(corpus_texts)

    kw_hits = 0
    tfidf_hits = 0
    total = len(queries)
    failed_queries = []

    print("=" * 70)
    print("SMART NOTES ASSISTANT - SEARCH RETRIEVAL BENCHMARK")
    print(f"Corpus: {len(corpus)} starter notes | Evaluation queries: {total}")
    print("=" * 70)

    for q in queries:
        qid = q["query_id"]
        qtext = q["query"]
        expected = set(q["expected_note_ids"])

        kw_res = keyword_search(qtext, corpus, top_k=3)
        kw_ids = [r["note_id"] for r in kw_res]
        kw_hit = len(expected.intersection(set(kw_ids))) > 0

        tfidf_res = tfidf_search(qtext, corpus, vectorizer, matrix, top_k=3)
        tfidf_ids = [r["note_id"] for r in tfidf_res]
        tfidf_hit = len(expected.intersection(set(tfidf_ids))) > 0

        if kw_hit:
            kw_hits += 1
        if tfidf_hit:
            tfidf_hits += 1
        else:
            failed_queries.append({
                "query_id": qid,
                "query": qtext,
                "expected": list(expected),
                "retrieved": tfidf_ids,
                "description": q.get("description", "")
            })

        print(f"[{qid}] Query: '{qtext}'")
        print(f"      Expected: {list(expected)}")
        print(f"      Keyword Top 3 : {kw_ids} -> {'HIT' if kw_hit else 'MISS'}")
        print(f"      TF-IDF Top 3  : {tfidf_ids} -> {'HIT' if tfidf_hit else 'MISS'}")

    kw_hit_rate = kw_hits / total
    tfidf_hit_rate = tfidf_hits / total

    print("\n" + "-" * 70)
    print("BENCHMARK SUMMARY (Hit Rate @ 3)")
    print("-" * 70)
    print(f"Keyword Search  : {kw_hits}/{total} = {kw_hit_rate:.1%}")
    print(f"TF-IDF Search   : {tfidf_hits}/{total} = {tfidf_hit_rate:.1%}")
    print("-" * 70)

    print(f"\nFailed TF-IDF Queries ({len(failed_queries)} total):")
    for fq in failed_queries:
        print(f"  - [{fq['query_id']}] '{fq['query']}'")
        print(f"    Target: {fq['expected']}, Retrieved: {fq['retrieved']}")
        print(f"    Reason: Zero lexical overlap with target note ('{fq['description']}')")

    return {
        "total_queries": total,
        "keyword_hit_rate_at_3": kw_hit_rate,
        "tfidf_hit_rate_at_3": tfidf_hit_rate,
        "failed_queries": failed_queries,
    }


if __name__ == "__main__":
    run_evaluation()
