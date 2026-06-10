#!/usr/bin/env python3
"""
academic_search.py — Unified academic paper search across Semantic Scholar, arXiv, and OpenAlex.

All APIs are free. API keys are optional and improve rate limits when provided.

Usage:
    python academic_search.py --source s2 "knowledge graph RAG" --limit 10
    python academic_search.py --source arxiv "ontology reasoning" --limit 5
    python academic_search.py --source openalex "urban forest remote sensing" --limit 10
    python academic_search.py --source all "evidence governance knowledge" --limit 5
    python academic_search.py --paper "ArXiv:2409.13731"
    python academic_search.py --citations "PAPER_ID" --limit 5
    python academic_search.py --dedup "query" --limit 10

Environment variables (optional):
    S2_API_KEY       — Semantic Scholar API key (improves rate limit from ~1/s to ~10/s)
    OPENALEX_EMAIL   — OpenAlex polite pool email (improves rate limit)

Design:
    - Zero mandatory dependencies (stdlib only: urllib, json, xml)
    - Unified output schema across all sources
    - Citation graph traversal (forward + backward)
    - Cross-source deduplication by DOI / arXiv ID
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Optional


# ── Config ─────────────────────────────────────────────────────────────────

S2_API_KEY = os.environ.get("S2_API_KEY", "")
OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "research@example.com")

S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,authors,year,abstract,citationCount,url,venue,externalIds,openAccessPdf,tldr"

ARXIV_API = "http://export.arxiv.org/api/query"
OPENALEX_API = "https://api.openalex.org"

# Unified output fields
UNIFIED_FIELDS = ["id", "title", "year", "authors", "venue", "citations",
                  "url", "abstract", "doi", "arxiv", "pdf", "tldr",
                  "source", "open_access"]


# ── HTTP helper ────────────────────────────────────────────────────────────

def _http_get(url: str, headers: Optional[dict] = None, retries: int = 3, timeout: int = 30) -> bytes:
    """HTTP GET with retry and backoff."""
    hdrs = {"User-Agent": "research-sprint/1.0"}
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


def _json_get(url: str, headers: Optional[dict] = None, retries: int = 3) -> dict:
    return json.loads(_http_get(url, headers, retries).decode())


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


def s2_paper(paper_id: str) -> dict:
    url = (f"{S2_BASE}/paper/{urllib.parse.quote(paper_id, safe='')}"
           f"?fields={S2_FIELDS},references.title,references.year,references.paperId,"
           f"citations.title,citations.year,citations.paperId,tldr")
    return _s2_fmt(_json_get(url, _s2_headers()), detailed=True)


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
        "pdf": (p.get("openAccessPdf") or {}).get("url", ""),
        "tldr": (p.get("tldr") or {}).get("text", ""),
        "source": "semantic_scholar",
        "open_access": bool((p.get("openAccessPdf") or {}).get("url")),
    }
    return result


# ── arXiv ──────────────────────────────────────────────────────────────────

def arxiv_search(query: str, limit: int = 10) -> list:
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    xml_data = _http_get(f"{ARXIV_API}?{params}", timeout=45).decode()
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
        results.append({
            "id": f"arxiv:{arxiv_id}",
            "title": title,
            "year": int(published[:4]),
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

def openalex_search(query: str, limit: int = 10, year_from: Optional[int] = None) -> list:
    params = {"search": query, "per_page": limit, "sort": "relevance_score:desc"}
    if year_from:
        params["filter"] = f"from_publication_date:{year_from}-01-01"
    url = f"{OPENALEX_API}/works?{urllib.parse.urlencode(params)}"
    data = _json_get(url, {"User-Agent": f"mailto:{OPENALEX_EMAIL}"})
    results = []
    for w in data.get("results", []):
        authorships = w.get("authorships") or []
        authors = ", ".join(
            a.get("author", {}).get("display_name", "?") for a in authorships[:5]
        )
        if len(authorships) > 5:
            authors += " et al."
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        results.append({
            "id": w.get("id", ""),
            "title": w.get("title", ""),
            "year": w.get("publication_year"),
            "venue": (w.get("primary_location") or {}).get("source", {}).get("display_name", "")
                     if w.get("primary_location") else "",
            "authors": authors,
            "citations": w.get("cited_by_count"),
            "url": w.get("doi") or w.get("id", ""),
            "abstract": _oa_abstract(w.get("abstract_inverted_index")),
            "doi": doi or None,
            "arxiv": None,
            "pdf": "",
            "tldr": "",
            "source": "openalex",
            "open_access": (w.get("open_access") or {}).get("is_oa", False),
        })
    return results


def _oa_abstract(inverted_index: Optional[dict]) -> str:
    if not inverted_index:
        return ""
    words = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))
    words.sort()
    return " ".join(w for _, w in words)[:500]


# ── Cross-source deduplication ─────────────────────────────────────────────

def dedup_papers(papers: list) -> list:
    """Deduplicate papers by DOI, arXiv ID, or title similarity."""
    seen = set()
    unique = []
    for p in papers:
        key = None
        if p.get("doi"):
            key = f"doi:{p['doi'].lower()}"
        elif p.get("arxiv"):
            key = f"arxiv:{p['arxiv']}"
        else:
            key = f"title:{p.get('title', '').lower().strip()[:80]}"
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def search_all(query: str, limit: int = 5, year_from: Optional[int] = None) -> dict:
    """Search all sources, deduplicate, and return combined results."""
    all_papers = []
    errors = {}

    # S2
    try:
        s2 = s2_search(query, limit, year_from)
        all_papers.extend(s2)
    except Exception as e:
        errors["semantic_scholar"] = str(e)

    # arXiv
    try:
        ax = arxiv_search(query, limit)
        all_papers.extend(ax)
    except Exception as e:
        errors["arxiv"] = str(e)

    # OpenAlex
    try:
        oa = openalex_search(query, limit, year_from)
        all_papers.extend(oa)
    except Exception as e:
        errors["openalex"] = str(e)

    # Sort by citation count (desc), nulls last
    all_papers.sort(key=lambda p: p.get("citations") or -1, reverse=True)
    deduped = dedup_papers(all_papers)

    return {
        "query": query,
        "total_raw": len(all_papers),
        "total_deduped": len(deduped),
        "papers": deduped[:limit * 3],
        "errors": errors if errors else None,
    }


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
    from datetime import date
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
            print(f"  {i:2d}. [{y}|{s}] {p.get('title', '')[:75]}  (cites:{c})")
        else:
            print(f"\n{'─'*60}")
            print(f"  [{i}] {p.get('title', 'No title')}")
            y = p.get('year', '?')
            v = p.get('venue', '-')
            c = p.get('citations', '?')
            s = p.get('source', '')
            print(f"  Year: {y} | Venue: {v} | Citations: {c} | Source: {s}")
            print(f"  Authors: {p.get('authors', '-')}")
            print(f"  URL: {p.get('url', '-')}")
            if p.get("arxiv"):
                print(f"  arXiv: {p['arxiv']}")
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
            print(f"  {k.upper()}: {p[k]}")
    if p.get("tldr"):
        print(f"\n  TL;DR: {p['tldr']}")
    if p.get("abstract"):
        print(f"\n  Abstract:\n  {p['abstract']}")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Research Sprint — Academic paper search (S2 + arXiv + OpenAlex)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --source s2 "knowledge graph RAG" --limit 10
  %(prog)s --source all "evidence governance" --dedup --limit 5
  %(prog)s --paper "ArXiv:2409.13731"
  %(prog)s --citations "PAPER_ID" --limit 5
  %(prog)s --source all "query" --save-card
        """,
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--source", choices=["s2", "arxiv", "openalex", "all"], default="s2",
                        help="Search source (default: s2)")
    parser.add_argument("--limit", type=int, default=10, help="Max results per source (default: 10)")
    parser.add_argument("--year-from", type=int, help="Filter by publication year (e.g. 2023)")
    parser.add_argument("--paper", help="Get paper details by S2/DOI/arXiv ID")
    parser.add_argument("--citations", help="Get papers citing this paper ID")
    parser.add_argument("--references", help="Get papers referenced by this paper ID")
    parser.add_argument("--dedup", action="store_true", help="Deduplicate cross-source results")
    parser.add_argument("--save-card", action="store_true", help="Generate paper card markdown")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--compact", action="store_true", help="Compact one-line output")

    args = parser.parse_args()

    # Paper detail
    if args.paper:
        result = s2_paper(args.paper)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.save_card:
            print(generate_card(result))
        else:
            _print_paper_detail(result)
        return

    # Citations
    if args.citations:
        results = s2_citations(args.citations, args.limit)
        _print_results(results, args.json, args.compact)
        return

    # References
    if args.references:
        results = s2_references(args.references, args.limit)
        _print_results(results, args.json, args.compact)
        return

    # Search
    if not args.query:
        parser.print_help()
        return

    if args.source == "all":
        data = search_all(args.query, args.limit, args.year_from)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        elif args.save_card:
            for p in data.get("papers", [])[:5]:
                print(generate_card(p))
                print("\n" + "=" * 60 + "\n")
        else:
            print(f"\n  Query: '{data['query']}' | Raw: {data['total_raw']} | After dedup: {data['total_deduped']}")
            if data.get("errors"):
                print(f"  Source errors: {data['errors']}")
            _print_results(data.get("papers", []), False, args.compact)
    else:
        if args.source == "s2":
            results = s2_search(args.query, args.limit, args.year_from)
        elif args.source == "arxiv":
            results = arxiv_search(args.query, args.limit)
        elif args.source == "openalex":
            results = openalex_search(args.query, args.limit, args.year_from)
        else:
            results = []

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


if __name__ == "__main__":
    main()
