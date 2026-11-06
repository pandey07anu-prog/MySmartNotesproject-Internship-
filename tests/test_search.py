"""
Tests for search engine: Keyword vs TF-IDF search, relevance ranking, and Hit Rate @ 3.
"""

import json
import pytest
from app.config import PROJECT_ROOT
from app.services.search import search_service


@pytest.fixture(scope="module")
def starter_corpus():
    starter_path = PROJECT_ROOT / "data" / "starter_notes.json"
    with open(starter_path, "r", encoding="utf-8") as f:
        notes = json.load(f)
    return [{"note_id": n["id"], "text": n["text"]} for n in notes]


def test_keyword_search_direct(starter_corpus):
    results = search_service.keyword_search("Python test", starter_corpus, top_k=3)
    assert len(results) > 0
    assert results[0]["note_id"] == "N001"


def test_tfidf_search_ranking(starter_corpus):
    results = search_service.tfidf_search("Delhi flight Monday", starter_corpus, top_k=3)
    assert len(results) > 0
    assert results[0]["note_id"] == "N003"
    assert results[0]["score"] > 0.05


def test_search_benchmark_hit_rate(starter_corpus):
    queries_path = PROJECT_ROOT / "data" / "search_queries.json"
    with open(queries_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    hits = 0
    for q in queries:
        expected = set(q["expected_note_ids"])
        res = search_service.tfidf_search(q["query"], starter_corpus, top_k=3)
        retrieved_ids = {r["note_id"] for r in res}
        if len(expected.intersection(retrieved_ids)) > 0:
            hits += 1

    hit_rate = hits / len(queries)
    # Expected benchmark: 80% (12 of 15 queries hit top 3; 3 vocabulary mismatch miss)
    assert hit_rate >= 0.80

