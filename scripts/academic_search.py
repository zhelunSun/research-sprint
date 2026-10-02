#!/usr/bin/env python3
"""
academic_search.py — Unified academic paper search across Semantic Scholar, arXiv,
OpenAlex, Crossref, and DuckDuckGo.

All APIs are free. API keys are optional and improve rate limits when provided.

Usage:
    python academic_search.py --source s2 "knowledge graph RAG" --limit 10
    python academic_search.py --source arxiv "ontology reasoning" --limit 5
    python academic_search.py --source openalex "urban forest remote sensing" --limit 10
    python academic_search.py --source crossref "provenance ontology W3C" --limit 5
    python academic_search.py --source ddg "KDD 2026 accepted papers" --limit 10
    python academic_search.py --source all "evidence governance knowledge" --limit 5
    python academic_search.py --paper "ArXiv:2409.13731"
    python academic_search.py --citations "PAPER_ID" --limit 5
    python academic_search.py --venue "NeurIPS" --year-from 2024 "knowledge graph LLM"

Environment variables (optional):
    S2_API_KEY       — Semantic Scholar API key (improves rate limit from ~1/s to ~10/s)
    OPENALEX_EMAIL   — OpenAlex polite pool email (improves rate limit)

Design:
    - Core APIs: S2 + arXiv + OpenAlex + Crossref (zero mandatory dependencies)
    - Optional: DuckDuckGo web search (needs: pip install duckduckgo-search)
    - Unified output schema across all sources
    - Citation graph traversal (forward + backward)
    - Cross-source deduplication by DOI / arXiv ID
    - Venue and author filtering (OpenAlex + Crossref)
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional


# ── Config ─────────────────────────────────────────────────────────────────

S2_API_KEY = os.environ.get("S2_API_KEY", "")
OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "research@example.com")

S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,authors,year,abstract,citationCount,url,venue,externalIds,openAccessPdf,tldr"

ARXIV_API = "https://export.arxiv.org/api/query"
OPENALEX_API = "https://api.openalex.org"
CROSSREF_API = "https://api.crossref.org"

# Unified output fields
UNIFIED_FIELDS = ["id", "title", "year", "authors", "venue", "citations",
                  "url", "abstract", "doi", "arxiv", "pdf", "tldr",
                  "source", "open_access"]

# Windows console encoding fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── HTTP helper ────────────────────────────────────────────────────────────

def _http_get(url: str, headers: Optional[dict] = None, retries: int = 2,
              timeout: int = 12) -> bytes:
    """HTTP GET with retry and exponential backoff.

    v0.3: timeout lowered 30→12s, retries 3→2 to avoid long hangs on slow sources.
    Use retries=1 for sources that should fail fast (arXiv).
    """
    hdrs = {"User-Agent": "research-sprint/2.0 (academic search)"}
    if headers:
        hdrs.update(headers)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))
            else:
                raise


def _json_get(url: str, headers: Optional[dict] = None, retries: int = 3,
              timeout: int = 30) -> dict:
    return json.loads(_http_get(url, headers, retries, timeout).decode())


def _safe_get(d: Optional[dict], *keys, default=""):
    """Safely traverse nested dicts."""
    current = d
    for key in keys:
        if current is None or not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


# ── Semantic Scholar ───────────────────────────────────────────────────────

def _s2_headers() -> dict:
    if S2_API_KEY:
        return {"x-api-key": S2_API_KEY}
    return {}


def s2_search(query: str, limit: int = 10, year_from: Optional[int] = None) -> list:
    params = f"query={urllib.parse.quote(query)}&limit={limit}&fields={S2_FIELDS}"
    if year_from:
        params += f"&year={year_from}-"
    data = _json_get(f"{S2_BASE}/paper/search?{params}", _s2_headers())
    return [_s2_fmt(p) for p in data.get("data", [])]


def s2_paper(paper_id: str) -> Optional[dict]:
    """Get paper details by S2/DOI/arXiv ID. Returns None if not found."""
    try:
        url = (f"{S2_BASE}/paper/{urllib.parse.quote(paper_id, safe='')}"
               f"?fields={S2_FIELDS},references.title,references.year,references.paperId,"
               f"citations.title,citations.year,citations.paperId,tldr")
        return _s2_fmt(_json_get(url, _s2_headers()), detailed=True)
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return None
        raise


def s2_citations(paper_id: str, limit: int = 10) -> list:
    url = (f"{S2_BASE}/paper/{urllib.parse.quote(paper_id, safe='')}/citations"
           f"?fields={S2_FIELDS}&limit={limit}")
    data = _json_get(url, _s2_headers())
    return [_s2_fmt(c.get("citingPaper", {})) for c in data.get("data", [])
            if c.get("citingPaper", {}).get("paperId")]


def s2_references(paper_id: str, limit: int = 10) -> list:
    url = (f"{S2_BASE}/paper/{urllib.parse.quote(paper_id, safe='')}/references"
           f"?fields={S2_FIELDS}&limit={limit}")
    data = _json_get(url, _s2_headers())
    return [_s2_fmt(r.get("citedPaper", {})) for r in data.get("data", [])
            if r.get("citedPaper", {}).get("paperId")]


def _s2_fmt(p: dict, detailed: bool = False) -> dict:
    authors = ", ".join(a.get("name", "?") for a in (p.get("authors") or [])[:5])
    if len((p.get("authors") or [])) > 5:
        authors += " et al."
    ext = p.get("externalIds") or {}
    result = {
        "id": p.get("paperId", ""),
        "title": p.get("title", ""),
        "year": p.get("year"),
        "venue": p.get("venue", ""),
        "authors": authors,
        "citations": p.get("citationCount"),
        "url": p.get("url", ""),
        "abstract": (p.get("abstract") or "")[:500],
        "doi": ext.get("DOI"),
        "arxiv": ext.get("ArXiv"),
        "pdf": _safe_get(p, "openAccessPdf", "url"),
        "tldr": _safe_get(p, "tldr", "text"),
        "source": "semantic_scholar",
        "open_access": bool(_safe_get(p, "openAccessPdf", "url")),
    }
    return result


# ── arXiv ──────────────────────────────────────────────────────────────────

def _arxiv_query_format(query: str) -> str:
    """Convert a natural language query to arXiv search format.

    arXiv API supports: ti: (title), abs: (abstract), au: (author), cat: (category)
    AND/OR/ANDNOT operators. Default is AND for space-separated terms.
    """
    # If the query already contains arXiv operators, use as-is
    if any(op in query for op in ["ti:", "abs:", "au:", "cat:", "AND", "OR"]):
        return query
    # Split into keywords and search title + abstract
    terms = query.strip().split()
    if len(terms) <= 3:
        return query  # Short queries work fine as-is
    # For longer queries, keep as-is (arXiv default AND behavior is usually ok)
    return query


def arxiv_search(query: str, limit: int = 10, year_from: Optional[int] = None) -> list:
    formatted_query = _arxiv_query_format(query)
    params = urllib.parse.urlencode({
        "search_query": formatted_query,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    try:
        xml_data = _http_get(f"{ARXIV_API}?{params}", retries=1, timeout=10).decode()
    except Exception as e:
        # arXiv often unreachable from CN networks; fail gracefully so
        # --source all doesn't crash. Caller sees empty list + error in report.
        sys.stderr.write(f"[arxiv] unreachable: {type(e).__name__}\n")
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_data)
    results = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:500]
        published = entry.find("atom:published", ns).text[:10]
        link = entry.find("atom:id", ns).text
        author_list = entry.findall("atom:author", ns)
        authors = ", ".join(a.find("atom:name", ns).text for a in author_list[:5])
        if len(author_list) > 5:
            authors += " et al."
        arxiv_id = link.split("/abs/")[-1]
        paper_year = int(published[:4])
        # Filter by year if specified
        if year_from and paper_year < year_from:
            continue
        results.append({
            "id": f"arxiv:{arxiv_id}",
            "title": title,
            "year": paper_year,
            "venue": "arXiv",
            "authors": authors,
            "citations": None,
            "url": link,
            "abstract": summary,
            "doi": None,
            "arxiv": arxiv_id,
            "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
            "tldr": "",
            "source": "arxiv",
            "open_access": True,
        })
    return results


# ── OpenAlex ───────────────────────────────────────────────────────────────

def _oa_extract_arxiv(work: dict) -> Optional[str]:
    """Extract arXiv ID from OpenAlex work record."""
    # Method 1: from DOI (e.g., 10.48550/arxiv.2412.16833)
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    if doi and "arxiv" in doi.lower():
        match = re.search(r"arxiv\.(\d+\.\d+)", doi, re.IGNORECASE)
        if match:
            return match.group(1)
    # Method 2: from best_oa_location landing_page_url
    for loc_key in ["best_oa_location", "primary_location"]:
        loc = work.get(loc_key) or {}
        landing = loc.get("landing_page_url") or ""
        if "arxiv.org" in landing:
            match = re.search(r"(\d{4}\.\d{4,5})", landing)
            if match:
                return match.group(1)
    # Method 3: from open_access.oa_url
    oa = work.get("open_access") or {}
    oa_url = oa.get("oa_url") or ""
    if "arxiv.org" in oa_url:
        match = re.search(r"(\d{4}\.\d{4,5})", oa_url)
        if match:
            return match.group(1)
    return None


# Venue name → OpenAlex source ID cache
_OA_VENUE_CACHE: dict[str, Optional[str]] = {}

# Known conference/journal name mappings (expand as needed)
_VENUE_ALIASES = {
    "neurips": "Neural Information Processing Systems",
    "nips": "Neural Information Processing Systems",
    "icml": "International Conference on Machine Learning",
    "iclr": "International Conference on Learning Representations",
    "aaai": "AAAI Conference on Artificial Intelligence",
    "kdd": "Knowledge Discovery and Data Mining",
    "sigkdd": "Knowledge Discovery and Data Mining",
    "cvpr": "Computer Vision and Pattern Recognition",
    "acl": "Annual Meeting of the Association for Computational Linguistics",
    "emnlp": "Conference on Empirical Methods in Natural Language Processing",
    "naacl": "North American Chapter of the Association for Computational Linguistics",
    "www": "The Web Conference",
    "sigmod": "ACM SIGMOD",
    "vldb": "Very Large Data Bases",
    "icde": "International Conference on Data Engineering",
    "iswc": "International Semantic Web Conference",
    "eswc": "Extended Semantic Web Conference",
    "coling": "International Conference on Computational Linguistics",
}


def _oa_resolve_venue(venue: str) -> Optional[str]:
    """Resolve a venue name to an OpenAlex source ID.

    Uses cache + API lookup. Returns source ID (e.g., 'S4306420609') or None.
    """
    if venue in _OA_VENUE_CACHE:
        return _OA_VENUE_CACHE[venue]

    # Try alias lookup first
    search_term = _VENUE_ALIASES.get(venue.lower(), venue)

    try:
        url = f"{OPENALEX_API}/sources?search={urllib.parse.quote(search_term)}&per_page=5"
        data = _json_get(url, {"User-Agent": f"mailto:{OPENALEX_EMAIL}"}, timeout=15)
        for s in data.get("results", []):
            sid = s.get("id", "").split("/")[-1]
            works_count = s.get("works_count", 0)
            # Accept source if it has works (skip 0-work entries)
            if sid.startswith("S") and works_count > 0:
                _OA_VENUE_CACHE[venue] = sid
                return sid
    except Exception:
        pass

    # Cache the miss too, to avoid repeated lookups
    _OA_VENUE_CACHE[venue] = None
    return None


def openalex_search(query: str, limit: int = 10, year_from: Optional[int] = None,
                    venue: Optional[str] = None, author: Optional[str] = None) -> list:
    """Search OpenAlex with optional venue and author filters.

    Venue filter: resolves name to source ID, uses primary_location.source.id.
    Author filter: uses raw_author_name.search for name matching.
    """
    filters = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if venue:
        source_id = _oa_resolve_venue(venue)
        if source_id:
            filters.append(f"primary_location.source.id:{source_id}")
        # If source not resolved, we'll post-filter by venue name
    if author:
        filters.append(f"raw_author_name.search:{author}")

    params = {
        "search": query,
        "per_page": limit * 2 if venue else limit,  # Over-fetch if post-filtering
        "sort": "relevance_score:desc",
    }
    if filters:
        params["filter"] = ",".join(filters)

    url = f"{OPENALEX_API}/works?{urllib.parse.urlencode(params)}"
    data = _json_get(url, {"User-Agent": f"mailto:{OPENALEX_EMAIL}"})
    results = []
    for w in data.get("results", []):
        # Post-filter by venue name if source ID wasn't resolved
        if venue and not _oa_resolve_venue(venue):
            vname = _safe_get(w, "primary_location", "source", "display_name").lower()
            if venue.lower() not in vname:
                continue

        authorships = w.get("authorships") or []
        authors = ", ".join(
            _safe_get(a, "author", "display_name") or "?"
            for a in authorships[:5]
        )
        if len(authorships) > 5:
            authors += " et al."
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        arxiv_id = _oa_extract_arxiv(w)
        results.append({
            "id": w.get("id", ""),
            "title": w.get("title", "") or "",
            "year": w.get("publication_year"),
            "venue": _safe_get(w, "primary_location", "source", "display_name"),
            "authors": authors,
            "citations": w.get("cited_by_count"),
            "url": w.get("doi") or w.get("id", ""),
            "abstract": _oa_abstract(w.get("abstract_inverted_index")),
            "doi": doi or None,
            "arxiv": arxiv_id,
            "pdf": _safe_get(w, "best_oa_location", "pdf_url") or "",
            "tldr": "",
            "source": "openalex",
            "open_access": _safe_get(w, "open_access", "is_oa", default=False),
        })
    return results[:limit]


def _oa_abstract(inverted_index: Optional[dict]) -> str:
    if not inverted_index:
        return ""
    words = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))
    words.sort()
    return " ".join(w for _, w in words)[:500]


# ── Crossref ───────────────────────────────────────────────────────────────

def crossref_search(query: str, limit: int = 10, year_from: Optional[int] = None,
                    venue: Optional[str] = None, author: Optional[str] = None) -> list:
    """Search Crossref for academic papers. Best for DOI metadata and venue info."""
    params = {
        "query.bibliographic": query,
        "rows": limit,
        "sort": "relevance",
    }
    filters = []
    if year_from:
        filters.append(f"from-pub-date:{year_from}")
    if venue:
        params["query.container-title"] = venue
    if author:
        params["query.author"] = author
    if filters:
        params["filter"] = ",".join(filters)

    url = f"{CROSSREF_API}/works?{urllib.parse.urlencode(params)}"
    data = _json_get(url, headers={"User-Agent": f"research-sprint/2.0 mailto:{OPENALEX_EMAIL}"})
    results = []
    for item in data.get("message", {}).get("items", []):
        # Extract authors
        cr_authors = item.get("author") or []
        author_names = ", ".join(
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in cr_authors[:5]
        )
        if len(cr_authors) > 5:
            author_names += " et al."

        # Extract year
        year = None
        for date_field in ["published-print", "published-online", "created"]:
            dp = _safe_get(item, date_field, "date-parts")
            if dp and isinstance(dp, list) and dp[0]:
                year = dp[0][0]
                break

        # Extract venue
        venue_name = ""
        containers = item.get("container-title") or []
        if containers:
            venue_name = containers[0]

        # Extract abstract (Crossref stores as JATS XML sometimes)
        abstract_raw = item.get("abstract") or ""
        # Strip JATS XML tags
        abstract_clean = re.sub(r'<[^>]+>', '', abstract_raw).strip()[:500]

        doi = item.get("DOI", "")

        results.append({
            "id": f"crossref:{doi}",
            "title": (item.get("title") or [""])[0],
            "year": year,
            "venue": venue_name,
            "authors": author_names,
            "citations": item.get("is-referenced-by-count"),
            "url": f"https://doi.org/{doi}" if doi else "",
            "abstract": abstract_clean,
            "doi": doi or None,
            "arxiv": None,  # Crossref doesn't easily expose arXiv IDs
            "pdf": _safe_get(item, "link", default=[]),
            "tldr": "",
            "source": "crossref",
            "open_access": item.get("is_oa", False),
        })
    return results


def crossref_paper(doi: str) -> Optional[dict]:
    """Get paper details from Crossref by DOI."""
    try:
        url = f"{CROSSREF_API}/works/{urllib.parse.quote(doi, safe='')}"
        data = _json_get(url, headers={"User-Agent": f"research-sprint/2.0 mailto:{OPENALEX_EMAIL}"})
        item = data.get("message", {})

        cr_authors = item.get("author") or []
        author_names = ", ".join(
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in cr_authors[:5]
        )

        year = None
        for date_field in ["published-print", "published-online", "created"]:
            dp = _safe_get(item, date_field, "date-parts")
            if dp and isinstance(dp, list) and dp[0]:
                year = dp[0][0]
                break

        containers = item.get("container-title") or []
        venue_name = containers[0] if containers else ""

        abstract_raw = item.get("abstract") or ""
        abstract_clean = re.sub(r'<[^>]+>', '', abstract_raw).strip()[:500]

        return {
            "id": f"crossref:{doi}",
            "title": (item.get("title") or [""])[0],
            "year": year,
            "venue": venue_name,
            "authors": author_names,
            "citations": item.get("is-referenced-by-count"),
            "url": f"https://doi.org/{doi}",
            "abstract": abstract_clean,
            "doi": doi,
            "arxiv": None,
            "pdf": "",
            "tldr": "",
            "source": "crossref",
            "open_access": item.get("is_oa", False),
        }
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return None
        raise


# ── DuckDuckGo Web Search ─────────────────────────────────────────────────

def ddg_search(query: str, limit: int = 10) -> list:
    """General web search via DuckDuckGo. No API key needed, unlimited.

    Requires: pip install duckduckgo-search
    Best for: finding specific papers, author pages, conference proceedings,
              blog posts, and general web queries.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return [{"error": "duckduckgo-search not installed. Run: pip install duckduckgo-search"}]

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=limit):
            results.append({
                "id": f"ddg:{hash(r.get('href', ''))}",
                "title": r.get("title", ""),
                "year": None,
                "venue": "",
                "authors": "",
                "citations": None,
                "url": r.get("href", ""),
                "abstract": r.get("body", "")[:500],
                "doi": None,
                "arxiv": None,
                "pdf": "",
                "tldr": "",
                "source": "duckduckgo",
                "open_access": False,
            })
    return results


# ── Multi-source paper lookup ──────────────────────────────────────────────

def get_paper(paper_id: str) -> Optional[dict]:
    """Look up a paper by ID, trying multiple sources with fallback.

    Supports: S2 paper ID, DOI:xxx, ArXiv:xxx, or a title string.
    Falls through S2 → Crossref → OpenAlex on errors.
    """
    if paper_id.startswith("DOI:"):
        doi = paper_id[4:]
        # Try S2 first (richest metadata)
        try:
            result = s2_paper(f"DOI:{doi}")
            if result and result.get("title"):
                return result
        except Exception:
            pass
        # Fallback to Crossref
        try:
            result = crossref_paper(doi)
            if result and result.get("title"):
                return result
        except Exception:
            pass
        return None

    if paper_id.startswith("ArXiv:") or paper_id.startswith("arXiv:"):
        arxiv_id = paper_id.split(":", 1)[1]
        # Try S2 first
        try:
            result = s2_paper(f"ArXiv:{arxiv_id}")
            if result and result.get("title"):
                return result
        except Exception:
            pass
        # Try Crossref with arXiv DOI
        try:
            result = crossref_paper(f"10.48550/arxiv.{arxiv_id}")
            if result and result.get("title"):
                return result
        except Exception:
            pass
        # Last resort: search OpenAlex by arXiv DOI
        try:
            oa_doi = f"https://doi.org/10.48550/arxiv.{arxiv_id}"
            params = {
                "filter": f"doi:{oa_doi}",
                "per_page": 1,
            }
            url = f"{OPENALEX_API}/works?{urllib.parse.urlencode(params)}"
            data = _json_get(url, {"User-Agent": f"mailto:{OPENALEX_EMAIL}"}, timeout=15)
            oa_results = data.get("results", [])
            if oa_results:
                w = oa_results[0]
                authorships = w.get("authorships") or []
                authors = ", ".join(
                    _safe_get(a, "author", "display_name") or "?"
                    for a in authorships[:5]
                )
                return {
                    "id": w.get("id", ""),
                    "title": w.get("title", ""),
                    "year": w.get("publication_year"),
                    "venue": _safe_get(w, "primary_location", "source", "display_name"),
                    "authors": authors,
                    "citations": w.get("cited_by_count"),
                    "url": w.get("doi") or w.get("id", ""),
                    "abstract": _oa_abstract(w.get("abstract_inverted_index")),
                    "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
                    "arxiv": arxiv_id,
                    "pdf": _safe_get(w, "best_oa_location", "pdf_url") or "",
                    "tldr": "",
                    "source": "openalex",
                    "open_access": _safe_get(w, "open_access", "is_oa", default=False),
                }
        except Exception:
            pass
        return None

    # Assume S2 paper ID
    try:
        result = s2_paper(paper_id)
        if result and result.get("title"):
            return result
    except Exception:
        pass
    return None


# ── Cross-source deduplication ─────────────────────────────────────────────

def dedup_papers(papers: list) -> list:
    """Deduplicate papers by DOI, arXiv ID, or title prefix."""
    seen = set()
    unique = []
    for p in papers:
        key = None
        if p.get("doi"):
            key = f"doi:{p['doi'].lower()}"
        elif p.get("arxiv"):
            key = f"arxiv:{p['arxiv']}"
        elif p.get("title"):
            key = f"title:{p.get('title', '').lower().strip()[:80]}"
        else:
            key = f"id:{p.get('id', id(p))}"
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


# Source mapping
ACADEMIC_SOURCES = {
    "s2": s2_search,
    "arxiv": arxiv_search,
    "openalex": openalex_search,
    "crossref": crossref_search,
}
ALL_ACADEMIC = ["s2", "arxiv", "openalex", "crossref"]


def search_all(query: str, limit: int = 5, year_from: Optional[int] = None,
               venue: Optional[str] = None, author: Optional[str] = None,
               include_s2: bool = False) -> dict:
    """Search all academic sources concurrently, deduplicate, and return combined results.

    v0.3: Parallel execution via ThreadPoolExecutor. Total time = max(source)
    instead of sum(sources). S2 skipped by default unless include_s2=True or
    S2_API_KEY is set (avoids 429 slowdown).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Decide which sources to query
    sources_to_query = list(ALL_ACADEMIC)
    skip_s2 = (not include_s2) and (not S2_API_KEY)
    if skip_s2:
        sources_to_query = [s for s in sources_to_query if s != "s2"]

    all_papers = []
    errors = {}

    def _run_source(src_name):
        try:
            fn = ACADEMIC_SOURCES[src_name]
            kwargs = {"query": query, "limit": limit, "year_from": year_from}
            if src_name in ("openalex", "crossref"):
                if venue:
                    kwargs["venue"] = venue
                if author:
                    kwargs["author"] = author
            return src_name, fn(**kwargs), None
        except Exception as e:
            return src_name, [], str(e)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_run_source, src): src for src in sources_to_query}
        for future in as_completed(futures):
            src_name, results, err = future.result()
            if err:
                errors[src_name] = err
            else:
                all_papers.extend(results)

    if skip_s2:
        errors["s2"] = "skipped (no S2_API_KEY; use --include-s2 to force)"

    # Sort: papers with citations first (desc), then no-citations
    all_papers.sort(key=lambda p: p.get("citations") or -1, reverse=True)
    deduped = dedup_papers(all_papers)

    return {
        "query": query,
        "total_raw": len(all_papers),
        "total_deduped": len(deduped),
        "papers": deduped[:limit * 3],
        "errors": errors if errors else None,
    }


# ── arXiv HTML full-text reader ────────────────────────────────────────────

def arxiv_html_url(arxiv_id: str) -> str:
    """Get the HTML version URL for an arXiv paper."""
    return f"https://arxiv.org/html/{arxiv_id}"


def arxiv_pdf_url(arxiv_id: str) -> str:
    """Get the PDF download URL for an arXiv paper."""
    return f"https://arxiv.org/pdf/{arxiv_id}"


# ── Paper card generation ──────────────────────────────────────────────────

CARD_TEMPLATE = """# {title}

> **检索日期**: {date}
> **来源**: {source} | **Venue**: {venue} | **Year**: {year}
> **DOI**: {doi} | **arXiv**: {arxiv}
> **引用数**: {citations}
> **URL**: {url}
> **相关性**: ⬜ 待评估

## 核心摘要
{abstract}

## 研究问题

## 方法

## 数据与评测

## 主要发现

## 局限性

## 对本研究的价值
- **直接支持**:
- **部分支持**:
- **挑战或质疑**:
- **可复用概念**:

## 后续追踪

## 引用风险
"""


def generate_card(paper: dict) -> str:
    """Generate a markdown paper card from a paper dict."""
    return CARD_TEMPLATE.format(
        title=paper.get("title", "Untitled"),
        date=date.today().isoformat(),
        source=paper.get("source", "unknown"),
        venue=paper.get("venue", "-"),
        year=paper.get("year", "?"),
        doi=paper.get("doi") or "-",
        arxiv=paper.get("arxiv") or "-",
        citations=paper.get("citations") or "?",
        url=paper.get("url") or "-",
        abstract=paper.get("abstract") or "No abstract available.",
    )


# ── Output formatting ──────────────────────────────────────────────────────

def _print_results(papers: list, as_json: bool, compact: bool):
    if as_json:
        print(json.dumps(papers, indent=2, ensure_ascii=False))
        return
    if not papers:
        print("No results found.")
        return
    if isinstance(papers, list) and papers and "error" in papers[0]:
        print(f"Error: {papers[0]['error']}")
        return
    for i, p in enumerate(papers, 1):
        if compact:
            y = p.get("year", "?")
            c = p.get("citations", "?")
            s = p.get("source", "")[:3]
            oa = "🟢" if p.get("open_access") else "⬜"
            print(f"  {i:2d}. [{y}|{s}] {p.get('title', '')[:72]}  (cites:{c}) {oa}")
        else:
            print(f"\n{'─'*60}")
            print(f"  [{i}] {p.get('title', 'No title')}")
            y = p.get('year', '?')
            v = p.get('venue', '-')
            c = p.get('citations', '?')
            s = p.get('source', '')
            oa = "🟢 OA" if p.get("open_access") else ""
            print(f"  Year: {y} | Venue: {v} | Citations: {c} | Source: {s} {oa}")
            print(f"  Authors: {p.get('authors', '-')}")
            print(f"  URL: {p.get('url', '-')}")
            if p.get("arxiv"):
                print(f"  arXiv: {p['arxiv']}")
                print(f"  HTML:  {arxiv_html_url(p['arxiv'])}")
            if p.get("doi"):
                print(f"  DOI: {p['doi']}")
            if p.get("pdf"):
                print(f"  PDF: {p['pdf']}")
            if p.get("tldr"):
                print(f"  TL;DR: {p['tldr']}")
            if p.get("abstract"):
                print(f"  Abstract: {p['abstract'][:300]}...")


def _print_paper_detail(p: dict):
    print(f"\n{'='*60}")
    print(f"  {p.get('title', 'No title')}")
    print(f"{'='*60}")
    print(f"  ID: {p.get('id', '-')}")
    print(f"  Year: {p.get('year', '?')} | Venue: {p.get('venue', '-')} | Citations: {p.get('citations', '?')}")
    print(f"  Authors: {p.get('authors', '-')}")
    print(f"  URL: {p.get('url', '-')}")
    for k in ["arxiv", "doi", "pdf"]:
        if p.get(k):
            label = k.upper()
            print(f"  {label}: {p[k]}")
    if p.get("arxiv"):
        print(f"  HTML:  {arxiv_html_url(p['arxiv'])}")
    if p.get("tldr"):
        print(f"\n  TL;DR: {p['tldr']}")
    if p.get("abstract"):
        print(f"\n  Abstract:\n  {p['abstract']}")


# ── Search logger ──────────────────────────────────────────────────────────

def log_search(action: str, params: dict, results_summary: dict, log_dir: str):
    """Append a search action log entry as JSON line.

    Each entry records: when, what, how, and how many — for audit and replay.
    """
    from pathlib import Path
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / f"search-{date.today().isoformat()}.jsonl"

    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "action": action,           # e.g. "search", "paper", "citations"
        "params": params,           # query, source, limit, year_from, venue, author
        "results": results_summary,  # total, returned, errors, top3_titles
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _results_summary(results, total: int = None, errors: dict = None) -> dict:
    """Build a compact results summary for logging."""
    if isinstance(results, dict) and "papers" in results:
        # search_all result
        papers = results.get("papers", [])
        return {
            "total_raw": results.get("total_raw", len(papers)),
            "total_deduped": results.get("total_deduped", len(papers)),
            "errors": results.get("errors"),
            "top3": [p.get("title", "")[:80] for p in papers[:3]],
        }
    elif isinstance(results, list):
        return {
            "total": total or len(results),
            "returned": len(results),
            "errors": errors,
            "top3": [p.get("title", "")[:80] for p in results[:3]],
        }
    elif isinstance(results, dict):
        # single paper detail
        return {
            "found": bool(results.get("title")),
            "title": results.get("title", "")[:80],
            "source": results.get("source", ""),
        }
    return {"total": 0}


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Research Sprint v0.3 — Academic paper search (S2 + arXiv + OpenAlex + Crossref + DDG, parallel)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --source s2 "knowledge graph RAG" --limit 10
  %(prog)s --source all "evidence governance" --dedup --limit 5
  %(prog)s --source ddg "KDD 2026 accepted papers"
  %(prog)s --source openalex "LLM agent" --venue "NeurIPS" --year-from 2024
  %(prog)s --source crossref "provenance W3C PROV" --limit 10
  %(prog)s --paper "ArXiv:2409.13731"
  %(prog)s --paper "DOI:10.1145/3701716.3715240"
  %(prog)s --citations "PAPER_ID" --limit 5
  %(prog)s --source all "query" --save-card
  %(prog)s --source arxiv "ontology" --html
        """,
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--source", choices=["s2", "arxiv", "openalex", "crossref", "ddg", "all"],
                        default="s2", help="Search source (default: s2)")
    parser.add_argument("--limit", type=int, default=10, help="Max results per source (default: 10)")
    parser.add_argument("--year-from", type=int, help="Filter by publication year (e.g. 2023)")
    parser.add_argument("--venue", type=str, help="Filter by venue/conference (OpenAlex, Crossref)")
    parser.add_argument("--author", type=str, help="Filter by author name (OpenAlex, Crossref)")
    parser.add_argument("--paper", help="Get paper details by S2/DOI/arXiv ID")
    parser.add_argument("--citations", help="Get papers citing this paper ID")
    parser.add_argument("--references", help="Get papers referenced by this paper ID")
    parser.add_argument("--dedup", action="store_true", help="Deduplicate cross-source results")
    parser.add_argument("--save-card", action="store_true", help="Generate paper card markdown")
    parser.add_argument("--html", action="store_true", help="Show arXiv HTML URL for results")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--compact", action="store_true", help="Compact one-line output")
    parser.add_argument("--include-s2", action="store_true",
                        help="Force include Semantic Scholar even without API key (may 429)")
    parser.add_argument("--log-dir", type=str, default="",
                        help="Directory to append search logs (JSONL format). e.g. ./search-logs")

    args = parser.parse_args()

    # Paper detail (multi-source)
    if args.paper:
        result = get_paper(args.paper)
        if result is None:
            if args.log_dir:
                log_search("paper", {"paper_id": args.paper}, {"found": False}, args.log_dir)
            print(f"Paper not found: {args.paper}")
            sys.exit(1)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.save_card:
            print(generate_card(result))
        else:
            _print_paper_detail(result)
        if args.log_dir:
            log_search("paper", {"paper_id": args.paper}, _results_summary(result), args.log_dir)
        return

    # Citations
    if args.citations:
        results = s2_citations(args.citations, args.limit)
        _print_results(results, args.json, args.compact)
        if args.log_dir:
            log_search("citations", {"paper_id": args.citations, "limit": args.limit},
                       _results_summary(results), args.log_dir)
        return

    # References
    if args.references:
        results = s2_references(args.references, args.limit)
        _print_results(results, args.json, args.compact)
        if args.log_dir:
            log_search("references", {"paper_id": args.references, "limit": args.limit},
                       _results_summary(results), args.log_dir)
        return

    # Search
    if not args.query:
        parser.print_help()
        return

    search_params = {
        "query": args.query, "source": args.source, "limit": args.limit,
        "year_from": args.year_from, "venue": args.venue, "author": args.author,
        "dedup": args.dedup,
    }

    if args.source == "all":
        data = search_all(args.query, args.limit, args.year_from, args.venue, args.author,
                          include_s2=args.include_s2)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        elif args.save_card:
            for p in data.get("papers", [])[:5]:
                print(generate_card(p))
                print("\n" + "=" * 60 + "\n")
        else:
            print(f"\n  Query: '{data['query']}' | Raw: {data['total_raw']} | After dedup: {data['total_deduped']}")
            if args.venue:
                print(f"  Venue filter: {args.venue}")
            if args.author:
                print(f"  Author filter: {args.author}")
            if data.get("errors"):
                print(f"  Source errors: {data['errors']}")
            _print_results(data.get("papers", []), False, args.compact)
        if args.log_dir:
            log_search("search", search_params, _results_summary(data), args.log_dir)
    elif args.source == "ddg":
        results = ddg_search(args.query, args.limit)
        _print_results(results, args.json, args.compact)
        if args.log_dir:
            log_search("search", search_params, _results_summary(results), args.log_dir)
    else:
        fn = ACADEMIC_SOURCES[args.source]
        kwargs = {"query": args.query, "limit": args.limit, "year_from": args.year_from}
        if args.source in ("openalex", "crossref"):
            if args.venue:
                kwargs["venue"] = args.venue
            if args.author:
                kwargs["author"] = args.author
        results = fn(**kwargs)

        if args.dedup:
            results = dedup_papers(results)

        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        elif args.save_card:
            for p in results[:5]:
                print(generate_card(p))
                print("\n" + "=" * 60 + "\n")
        else:
            _print_results(results, False, args.compact)
        if args.log_dir:
            log_search("search", search_params, _results_summary(results), args.log_dir)

    # Show HTML URLs if requested
    if args.html and args.source in ("arxiv", "all"):
        print("\n  📖 arXiv HTML URLs (for full-text reading):")


if __name__ == "__main__":
    main()
