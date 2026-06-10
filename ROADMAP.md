# ROADMAP — Research Sprint

> Internal design notes and future development plan.
> This document is NOT for public distribution.

---

## Design Decisions Log

### 2026-06-10: Initial Architecture

**Decision: Three-layer architecture (API → CLI → Skill)**

| Layer | Component | Role |
|---|---|---|
| L1 | Free APIs (S2/arXiv/OpenAlex) | Raw data access |
| L2 | `academic_search.py` CLI | Unified search + dedup + format |
| L3 | `SKILL.md` | Claude Code workflow integration |

Why this separation:
- Layer 2 can be used standalone without Claude Code (just a CLI tool)
- Layer 3 can be swapped without touching the search engine
- Layer 1 sources can be added/removed independently

**Decision: Zero mandatory dependencies**

Three reasons:
1. PhD researchers often work in locked-down conda/venv environments
2. `urllib` + `json` + `xml.etree` cover all three APIs sufficiently
3. Eliminates install friction — clone and run

**Decision: Optional API keys via environment variables**

Pattern: `S2_API_KEY`, `OPENALEX_EMAIL`. No config file, no `.env` dependency.
- If key is set → use it (better rate limits)
- If not set → proceed without (works, just slower for S2)

**Decision: Unified output schema**

Every source normalizes to:
```
id, title, year, authors, venue, citations, url, abstract,
doi, arxiv, pdf, tldr, source, open_access
```
This allows cross-source deduplication and uniform downstream processing.

---

## Feature Backlog

### v0.2 — Polish (next sprint)
- [ ] S2 API key support in `_s2_headers()` — done, reading env var
- [ ] Title-similarity dedup (beyond exact DOI/arXiv match)
- [ ] `--output-dir` flag to save cards directly to a directory
- [ ] Config file support (`.research-sprint.yml`) for default source, limit, output paths
- [ ] Citation count-based ranking across sources in `search_all()`

### v0.3 — MCP Server (major milestone)
- [ ] Refactor to MCP server using `FastMCP`
- [ ] Tools: `search_papers`, `get_paper`, `get_citations`, `get_references`, `generate_card`
- [ ] Dual-mode: CLI + MCP server in same package
- [ ] Publish to PyPI (`pip install research-sprint`)
- [ ] Smithery integration (`npx @smithery/cli install`)

### v0.4 — Evidence Workflow
- [ ] `evidence_matrix` tool — auto-update CSV with claim→evidence mapping
- [ ] `gap_map` tool — compare paper coverage against a research question
- [ ] Zotero integration (read existing library, avoid re-searching known papers)
- [ ] `.bib` export for LaTeX workflows

### v0.5 — Advanced
- [ ] Embedding-based semantic dedup (requires optional dependency)
- [ ] PDF full-text extraction (via `pypdf` or `marker`)
- [ ] Local SQLite cache for searched papers
- [ ] ArXiv daily digest / RSS monitoring

---

## MCP Server Design (v0.3 target)

### Architecture

```
research-sprint-mcp/
├── pyproject.toml
├── src/
│   └── research_sprint_mcp/
│       ├── __init__.py
│       ├── server.py          # FastMCP server with tool definitions
│       ├── search.py          # Search logic (extracted from CLI)
│       ├── dedup.py           # Deduplication logic
│       └── card.py            # Paper card generation
├── claude-code/
│   └── SKILL.md               # Skill mode (lightweight install)
├── tests/
│   ├── test_search.py
│   ├── test_dedup.py
│   └── test_card.py
├── README.md
└── LICENSE
```

### MCP Tool Definitions

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research-sprint")

@mcp.tool()
def search_papers(query: str, sources: str = "all",
                  limit: int = 10, year_from: int | None = None) -> str:
    """Search academic papers across Semantic Scholar, arXiv, and OpenAlex.
    Returns deduplicated, ranked results."""

@mcp.tool()
def get_paper(paper_id: str) -> str:
    """Get detailed info for a paper by S2 ID, DOI, or arXiv ID."""

@mcp.tool()
def get_citations(paper_id: str, limit: int = 10) -> str:
    """Get papers that cite this paper (forward citation graph)."""

@mcp.tool()
def get_references(paper_id: str, limit: int = 10) -> str:
    """Get papers referenced by this paper (backward citation graph)."""

@mcp.tool()
def generate_card(paper_id: str) -> str:
    """Generate a structured markdown paper card for knowledge management."""
```

### Competitive Positioning vs Existing Tools

| Tool | Type | Our Differentiator |
|---|---|---|
| paper-search-mcp | MCP (20+ sources) | We add citation graph + paper cards + dedup; they add PDF download |
| semantic-scholar-mcp | MCP (S2 only) | We add multi-source + dedup + card generation |
| academic-research-skills | Skill (workflow) | We add a real search engine, not just prompts |
| ScholarAI | SaaS (paid) | We are free, open-source, local-first |

**Our niche**: The intersection of "free multi-source search" + "citation graph" + "structured paper cards" + "zero dependencies". No other tool covers all four.

---

## Testing Notes

### S2 Rate Limits
- Anonymous: ~1 request/second, bursts get 429
- With API key: ~10 requests/second
- Mitigation: exponential backoff (already implemented), interleave with arXiv/OpenAlex

### arXiv API
- No rate limit issues
- Search precision is lower (full-text matching, no relevance ranking)
- Best for CS/AI papers where arXiv is primary venue

### OpenAlex API
- No rate limit issues with polite pool (email header)
- Best metadata quality (citation counts, OA status, venue)
- Abstract in inverted index format (already handled)

---

## Origin Story

Built for a PhD thesis on knowledge-enhanced LLM agents for urban forest remote sensing. The tool was created because:
1. Existing deep research tools (Gemini, ChatGPT) produce reports but not structured paper cards
2. Existing MCP tools (paper-search-mcp) are great for search but don't produce research-ready artifacts
3. Citation graph traversal was a missing feature in all alternatives
4. Zero-dependency requirement came from working in a conda-managed research environment
