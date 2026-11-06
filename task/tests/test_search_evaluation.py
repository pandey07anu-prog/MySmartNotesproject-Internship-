"""
Automated Test Suite for Smart Notes Assistant - Search Evaluation & Benchmarking
Phase 6: Search Engine Development, Retrieval Benchmarking & Selection

Tests:
- Hit Rate @ 3 mathematical calculation.
- Hits at rank 1, rank 2, rank 3.
- Miss when expected note is at rank 4 or absent.
- Handling of multiple expected IDs.
- Programmatic verification of zero content-word overlap in vocabulary-mismatched queries.
- Ground truth isolation: verifying retrieval algorithms do not access expected IDs.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from evaluate_search import evaluate_retrieval, verify_vocabulary_mismatch
from src.data_ingestion import get_project_root


@pytest.fixture
def starter_corpus():
    root = get_project_root()
    starter_file = root / "data" / "starter_notes.json"
    with open(starter_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def benchmark_queries():
    root = get_project_root()
    queries_file = root / "data" / "search_queries.json"
    with open(queries_file, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Hit Rate @ 3 Metric Computation
# ---------------------------------------------------------------------------
def test_hit_rate_at_3_ranks(starter_corpus):
    # Query matching N001 at rank 1
    q_rank1 = [{"query_id": "T01", "query": "Python test", "expected_note_ids": ["N001"]}]
    eval_rank1 = evaluate_retrieval(starter_corpus, q_rank1, top_k=3)
    assert eval_rank1["tfidf"]["total_hits"] == 1
    assert eval_rank1["tfidf"]["hit_rate_overall"] == 100.0

    # Query with multiple expected IDs where at least one is in top 3
    q_multi = [{"query_id": "T02", "query": "Python test", "expected_note_ids": ["N001", "N999"]}]
    eval_multi = evaluate_retrieval(starter_corpus, q_multi, top_k=3)
    assert eval_multi["tfidf"]["total_hits"] == 1


def test_miss_when_expected_is_absent(starter_corpus):
    # Query with no matching note in corpus
    q_miss = [{"query_id": "T03", "query": "aerospace rocket propulsion", "expected_note_ids": ["N001"]}]
    eval_miss = evaluate_retrieval(starter_corpus, q_miss, top_k=3)
    assert eval_miss["tfidf"]["total_hits"] == 0
    assert eval_miss["tfidf"]["hit_rate_overall"] == 0.0


# ---------------------------------------------------------------------------
# 2. Vocabulary Mismatch Zero-Overlap Verification
# ---------------------------------------------------------------------------
def test_vocabulary_mismatch_verification_programmatic(starter_corpus, benchmark_queries):
    corpus_map = {n["id"]: n["text"] for n in starter_corpus}
    mismatched = [q for q in benchmark_queries if q.get("query_type") == "vocabulary_mismatch"]

    # Must contain at least 3 vocabulary-mismatched queries
    assert len(mismatched) >= 3

    for q in mismatched:
        query_text = q["query"]
        for expected_id in q["expected_note_ids"]:
            target_text = corpus_map[expected_id]
            is_zero, q_words, n_words, overlap = verify_vocabulary_mismatch(query_text, target_text)

            # Programmatically assert zero shared content words
            assert is_zero, f"Query '{query_text}' shares content words {overlap} with note '{target_text}'"
            assert len(overlap) == 0


# ---------------------------------------------------------------------------
# 3. Ground Truth Isolation
# ---------------------------------------------------------------------------
def test_ground_truth_isolation(starter_corpus):
    """
    Verify that search functions operate without knowledge of expected IDs.
    """
    from src.search_engine import keyword_search, tfidf_search

    query = "statistics assignment"
    # Search functions only accept (query, notes, top_k)
    kw_res = keyword_search(query, starter_corpus, top_k=3)
    tf_res = tfidf_search(query, starter_corpus, top_k=3)

    for res in kw_res + tf_res:
        # Notes returned must not contain ground truth inspection keys
        assert "expected_note_ids" not in res
        assert "is_ground_truth" not in res

