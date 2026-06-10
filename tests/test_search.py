#!/usr/bin/env python3
"""Basic tests for academic_search.py — run with: python tests/test_search.py"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from academic_search import (
    s2_search, s2_paper, s2_citations, s2_references,
    arxiv_search, openalex_search, search_all, dedup_papers,
    generate_card, _oa_abstract,
)

NETWORK_SKIP = os.environ.get("SKIP_NETWORK_TESTS", "")


def test_arxiv_search():
    """arXiv search should return results with expected fields."""
    print("Testing arXiv search...", end=" ")
    try:
        results = arxiv_search("transformer attention mechanism", limit=3)
        assert isinstance(results, list), "Should return a list"
        assert len(results) > 0, "Should return at least one result"
        p = results[0]
        assert "title" in p, "Each result should have 'title'"
        assert "arxiv" in p, "Each result should have 'arxiv' ID"
        assert "url" in p, "Each result should have 'url'"
        assert "pdf" in p, "Each result should have 'pdf' link"
        assert p["source"] == "arxiv", "Source should be 'arxiv'"
        print(f"OK — got {len(results)} results, e.g. '{p['title'][:50]}...'")
    except Exception as e:
        if "timed out" in str(e) or "429" in str(e):
            print(f"SKIP — network issue ({type(e).__name__})")
        else:
            raise


def test_openalex_search():
    """OpenAlex search should return results with citation counts."""
    print("Testing OpenAlex search...", end=" ")
    try:
        results = openalex_search("large language model agent", limit=3)
        assert isinstance(results, list), "Should return a list"
        assert len(results) > 0, "Should return at least one result"
        p = results[0]
        assert "title" in p, "Each result should have 'title'"
        assert "citations" in p, "Each result should have 'citations'"
        assert p["source"] == "openalex", "Source should be 'openalex'"
        print(f"OK — got {len(results)} results, e.g. '{p['title'][:50]}...' (cites: {p['citations']})")
    except Exception as e:
        if "timed out" in str(e) or "429" in str(e):
            print(f"SKIP — network issue ({type(e).__name__})")
        else:
            raise


def test_s2_search():
    """Semantic Scholar search should return results."""
    print("Testing S2 search...", end=" ")
    try:
        results = s2_search("knowledge graph retrieval augmented generation", limit=3)
        assert isinstance(results, list), "Should return a list"
        if results:
            p = results[0]
            assert "title" in p, "Each result should have 'title'"
            assert "id" in p, "Each result should have 'id'"
            assert p["source"] == "semantic_scholar", "Source should be 'semantic_scholar'"
            print(f"OK — got {len(results)} results, e.g. '{p['title'][:50]}...'")
        else:
            print("OK (no results, possibly rate-limited)")
    except Exception as e:
        if "429" in str(e) or "timed out" in str(e):
            print("SKIP — rate limited (expected without API key)")
        else:
            raise


def test_dedup():
    """Deduplication should remove duplicates by DOI and arXiv ID."""
    print("Testing dedup...", end=" ")
    papers = [
        {"title": "Paper A", "doi": "10.1234/test", "arxiv": None},
        {"title": "Paper A (duplicate)", "doi": "10.1234/test", "arxiv": None},
        {"title": "Paper B", "doi": None, "arxiv": "2401.00001"},
        {"title": "Paper B (duplicate)", "doi": None, "arxiv": "2401.00001"},
        {"title": "Paper C", "doi": None, "arxiv": None},
    ]
    result = dedup_papers(papers)
    assert len(result) == 3, f"Should have 3 unique papers, got {len(result)}"
    print(f"OK — 5 input → {len(result)} unique")


def test_oa_abstract():
    """OpenAlex abstract reconstruction should work."""
    print("Testing OA abstract...", end=" ")
    inverted = {"Hello": [0], "world": [1], "test": [2]}
    result = _oa_abstract(inverted)
    assert result == "Hello world test", f"Expected 'Hello world test', got '{result}'"
    # Also test empty
    assert _oa_abstract(None) == "", "Should return empty string for None"
    assert _oa_abstract({}) == "", "Should return empty string for empty dict"
    print("OK")


def test_generate_card():
    """Paper card generation should produce valid markdown."""
    print("Testing card generation...", end=" ")
    paper = {
        "title": "Test Paper Title",
        "source": "semantic_scholar",
        "venue": "NeurIPS",
        "year": 2025,
        "doi": "10.1234/test",
        "arxiv": "2501.00001",
        "citations": 42,
        "url": "https://example.com",
        "abstract": "This is a test abstract.",
    }
    card = generate_card(paper)
    assert "# Test Paper Title" in card, "Card should have title as heading"
    assert "NeurIPS" in card, "Card should mention venue"
    assert "10.1234/test" in card, "Card should mention DOI"
    assert "2501.00001" in card, "Card should mention arXiv ID"
    assert "42" in card, "Card should mention citation count"
    assert "研究问题" in card, "Card should have research question section"
    assert "方法" in card, "Card should have method section"
    print("OK — card generated correctly")


def test_search_all_structure():
    """search_all should return the expected structure."""
    print("Testing search_all (OpenAlex)...", end=" ")
    try:
        result = search_all("ontology knowledge graph", limit=2)
        assert "query" in result, "Should have 'query' field"
        assert "total_raw" in result, "Should have 'total_raw' field"
        assert "total_deduped" in result, "Should have 'total_deduped' field"
        assert "papers" in result, "Should have 'papers' field"
        assert isinstance(result["papers"], list), "Papers should be a list"
        print(f"OK — raw: {result['total_raw']}, deduped: {result['total_deduped']}")
    except Exception as e:
        if "timed out" in str(e) or "429" in str(e):
            print(f"SKIP — network issue ({type(e).__name__})")
        else:
            raise


def test_unified_schema():
    """All search results should have the unified output fields."""
    print("Testing unified schema...", end=" ")
    try:
        results = openalex_search("test", limit=1)
        if results:
            p = results[0]
            required = ["id", "title", "year", "authors", "venue", "citations",
                        "url", "abstract", "doi", "arxiv", "pdf", "source", "open_access"]
            missing = [f for f in required if f not in p]
            assert not missing, f"Missing fields: {missing}"
            print(f"OK — all {len(required)} fields present")
        else:
            print("SKIP — no results")
    except Exception as e:
        if "timed out" in str(e) or "429" in str(e):
            print(f"SKIP — network issue ({type(e).__name__})")
        else:
            raise


def run_all():
    """Run all tests with friendly output."""
    tests = [
        test_arxiv_search,
        test_openalex_search,
        test_s2_search,
        test_dedup,
        test_oa_abstract,
        test_generate_card,
        test_search_all_structure,
        test_unified_schema,
    ]
    passed = 0
    skipped = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL — {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            if "timed out" in str(e) or "429" in str(e):
                print(f"SKIP — {t.__name__}: network issue")
                skipped += 1
            else:
                print(f"ERROR — {t.__name__}: {e}")
                failed += 1
    total = passed + skipped + failed
    print(f"\n{'='*50}")
    print(f"  Results: {passed} passed, {skipped} skipped, {failed} failed ({total} total)")
    if skipped > 0:
        print(f"  Note: skipped tests require network access or API key")
    print(f"{'='*50}")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
