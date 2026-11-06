"""
Smart Notes Assistant - Search Engine Module
Phase 6: Search Engine Development, Retrieval Benchmarking & Selection

This module provides two distinct search implementations:
1. Keyword-based search baseline with token coverage and frequency scoring.
2. TF-IDF vectorizer + Cosine Similarity search using scikit-learn.

Guarantees:
- Deterministic ranking with tie-breaking on note ID.
- Configurable top_k result limit.
- Clean handling of zero-vector queries, empty vocabulary, and empty corpora.
- Never modifies input notes.
- Completely isolated from evaluation ground-truth IDs.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SUPPORTED_SEARCH_METHODS = ("tfidf", "keyword")
DEFAULT_SEARCH_METHOD = "tfidf"

# Standard English stopwords for lexical matching normalization
STANDARD_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've",
    "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves"
}


def validate_search_inputs(query: Any, top_k: Any) -> Tuple[str, int]:
    """
    Validate search query and top_k parameter.
    
    Raises:
        TypeError: If query is not a string or top_k is not an integer.
        ValueError: If query is empty/whitespace or top_k is <= 0.
    """
    if not isinstance(query, str):
        raise TypeError(f"Search query must be a string, got {type(query).__name__}: {query!r}")

    stripped_query = query.strip()
    if not stripped_query:
        raise ValueError("Search query cannot be empty or whitespace-only.")

    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError(f"top_k must be an integer, got {type(top_k).__name__}: {top_k!r}")

    if top_k <= 0:
        raise ValueError(f"top_k must be a positive integer >= 1, got {top_k}")

    return stripped_query, top_k


def tokenize_text(text: str) -> List[str]:
    """
    Tokenize text into lowercase alphanumeric and word tokens,
    preserving Unicode characters and numbers.
    """
    return re.findall(r"(?u)\b\w+\b", text.lower())


def keyword_search(
    query: str,
    notes: List[Dict[str, Any]],
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Perform deterministic keyword-based search over a collection of notes.
    
    Scoring Formula:
    Let Q be the set of meaningful query tokens (excluding common English stopwords).
    Let D be the list of tokens in the note.
    Let M = Q ∩ set(D) be the set of matching query terms present in the note.
    
    If |M| == 0:
        Score = 0.0 (Note is excluded from results).
    Else:
        1. Query Coverage:
           coverage = |M| / |Q|  (proportion of query tokens satisfied, in [0, 1])
        2. Term Density / Frequency:
           tf = sum_{t in M} (count(t in D) / |D|)
        3. Exact Substring Bonus:
           bonus = 0.5 if normalized query is an exact substring of note text, else 0.0
        
        Total Relevance Score = round(coverage + 0.5 * tf + bonus, 4)
        
    Deterministic Tie-Breaking:
    Results are sorted by (-score, note["id"]).
    """
    valid_query, valid_top_k = validate_search_inputs(query, top_k)

    if not notes:
        return []

    q_tokens = tokenize_text(valid_query)
    filtered_q = [t for t in q_tokens if t not in STANDARD_STOPWORDS]
    active_q = filtered_q if filtered_q else q_tokens

    if not active_q:
        return []

    q_set = set(active_q)
    norm_query_str = " ".join(active_q)
    scored_candidates: List[Tuple[float, str, Dict[str, Any]]] = []

    for note in notes:
        note_text = note.get("text", "")
        d_tokens = tokenize_text(note_text)
        if not d_tokens:
            continue

        d_set = set(d_tokens)
        matched_terms = q_set & d_set
        if not matched_terms:
            continue

        coverage = len(matched_terms) / len(q_set)
        tf_density = sum(d_tokens.count(t) for t in matched_terms) / len(d_tokens)

        # Exact normalized phrase match bonus
        norm_note_str = " ".join(d_tokens)
        exact_bonus = 0.5 if norm_query_str in norm_note_str else 0.0

        score = round(coverage + (0.5 * tf_density) + exact_bonus, 4)
        if score > 0.0:
            scored_candidates.append((score, str(note.get("id", "")), note))

    # Sort descending by score, ascending by note ID for deterministic tie-breaking
    scored_candidates.sort(key=lambda item: (-item[0], item[1]))

    results: List[Dict[str, Any]] = []
    for rank, (score, _, note_obj) in enumerate(scored_candidates[:valid_top_k], start=1):
        record = copy.deepcopy(note_obj)
        record["score"] = score
        record["rank"] = rank
        results.append(record)

    return results


def tfidf_search(
    query: str,
    notes: List[Dict[str, Any]],
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Perform TF-IDF Vectorizer + Cosine Similarity search over notes.
    
    Methodology:
    1. Fits a dedicated TfidfVectorizer on the current note corpus (with stopword filtering).
    2. Transforms the search query into the identical vector space.
    3. If query contains no vocabulary tokens (zero vector), returns an empty list.
    4. Computes cosine similarity:
       sim(q, d) = (q · d) / (||q||_2 * ||d||_2)  in [0.0, 1.0].
    5. Discards zero or non-meaningful matches (sim <= 1e-5).
    6. Sorts deterministically by (-sim, note["id"]).
    7. Returns top_k notes with 'score' and 'rank'.
    """
    valid_query, valid_top_k = validate_search_inputs(query, top_k)

    if not notes:
        return []

    corpus = [note.get("text", "") for note in notes]
    # Check if corpus has any non-empty text
    if not any(text.strip() for text in corpus):
        return []

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        token_pattern=r"(?u)\b\w+\b"
    )

    try:
        doc_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Raised if vocabulary is completely empty after stopword removal
        return []

    # Check if vectorizer extracted any features
    if len(vectorizer.vocabulary_) == 0:
        return []

    q_vec = vectorizer.transform([valid_query])
    if q_vec.nnz == 0:
        # Zero-vector query: no query terms exist in the corpus vocabulary
        return []

    sims = cosine_similarity(q_vec, doc_matrix)[0]
    scored_candidates: List[Tuple[float, str, Dict[str, Any]]] = []

    for idx, sim_score in enumerate(sims):
        sim_float = float(sim_score)
        if sim_float > 1e-5:
            note_obj = notes[idx]
            scored_candidates.append(
                (round(sim_float, 4), str(note_obj.get("id", "")), note_obj)
            )

    # Deterministic tie-breaking: score descending, ID ascending
    scored_candidates.sort(key=lambda item: (-item[0], item[1]))

    results: List[Dict[str, Any]] = []
    for rank, (score, _, note_obj) in enumerate(scored_candidates[:valid_top_k], start=1):
        record = copy.deepcopy(note_obj)
        record["score"] = score
        record["rank"] = rank
        results.append(record)

    return results


def search_notes(
    query: str,
    notes: List[Dict[str, Any]],
    method: str = DEFAULT_SEARCH_METHOD,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Unified public search interface.
    
    Args:
        query: Search string.
        notes: Collection of note dictionaries.
        method: Search algorithm ('tfidf' or 'keyword'). Defaults to 'tfidf'.
        top_k: Maximum number of ranked results to return.
        
    Returns:
        List of matching note dictionaries enriched with 'score' and 'rank'.
        
    Raises:
        ValueError: If method is unsupported.
    """
    if method not in SUPPORTED_SEARCH_METHODS:
        raise ValueError(
            f"Unsupported search method: '{method}'. Must be one of {list(SUPPORTED_SEARCH_METHODS)}"
        )

    if method == "keyword":
        return keyword_search(query=query, notes=notes, top_k=top_k)
    else:
        return tfidf_search(query=query, notes=notes, top_k=top_k)

