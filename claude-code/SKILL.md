# Research Sprint — Academic Literature Search & Structured Evidence Capture

## Trigger
When the user mentions any of: "research sprint", "lit search", "find papers", "literature review", "paper search", "evidence map", "gap map", "search papers", "文献搜索", "文献调研", "找论文".

## Overview
A structured academic research workflow with multi-source search (S2, arXiv, OpenAlex, Crossref), general web search (DuckDuckGo), and browser-based access (Playwright MCP). Produces ranked candidate tables, structured paper cards, and evidence annotations — designed for researchers who need traceable, auditable literature pipelines.

## Prerequisites
- Python 3.8+ (stdlib only for core academic search)
- Optional: `S2_API_KEY` env var for faster Semantic Scholar access
- Optional: `pip install duckduckgo-search` for general web search
- Optional: Playwright MCP (configured in `.mcp.json`) for browser-based search

## Search Matrix

| Source | Type | Best For | Limit |
|---|---|---|---|
| `--source all` | Multi-source dedup | Comprehensive academic search | S2 may 429 |
| `--source s2` | Semantic Scholar API | TLDR, citation graph | ~1/s without key |
| `--source arxiv` | arXiv API | CS/AI preprints, full-text | No limit |
| `--source openalex` | OpenAlex API | Metadata, venue/author filter | No limit |
| `--source crossref` | Crossref API | DOI metadata, journals | No limit |
| `--source ddg` | DuckDuckGo | General web, author pages | No limit |
| Playwright MCP | Browser | Semantic Scholar web, arXiv HTML | Google blocks |

## Core Tool
```bash
SCRIPT="D:/Projects/skills/research-sprint/scripts/academic_search.py"
```

### Available Commands
```bash
# Multi-source search with deduplication
python $SCRIPT --source all "query" --dedup --limit 10 --compact

# Single source
python $SCRIPT --source s2 "query" --limit 10 --compact
python $SCRIPT --source arxiv "query" --limit 10 --compact
python $SCRIPT --source openalex "query" --limit 10 --compact
python $SCRIPT --source crossref "query" --limit 10 --compact
python $SCRIPT --source ddg "query" --limit 10 --compact

# With venue and author filtering (OpenAlex, Crossref)
python $SCRIPT --source openalex "query" --venue "AAAI" --year-from 2024
python $SCRIPT --source crossref "query" --author "Guarino" --limit 5

# Paper details (multi-source fallback: S2 → Crossref → OpenAlex)
python $SCRIPT --paper "ArXiv:2409.13731"
python $SCRIPT --paper "DOI:10.1145/3701716.3715240"

# Citation graph traversal (S2 only)
python $SCRIPT --citations "PAPER_ID" --limit 10
python $SCRIPT --references "PAPER_ID" --limit 10

# Generate paper card markdown
python $SCRIPT --source all "query" --limit 5 --save-card

# JSON output for pipelines
python $SCRIPT --source all "query" --json
```

### Browser-Based Search (Playwright MCP)
When API search is insufficient (e.g., need visual browsing, Semantic Scholar web features):
```
# Navigate to Semantic Scholar (recommended — works reliably)
browser_navigate: https://www.semanticscholar.org/search?q=QUERY&sort=relevance

# Read arXiv paper full text (HTML version)
browser_navigate: https://arxiv.org/html/PAPER_ID

# Google Scholar: BLOCKED by anti-bot detection — do not use
```

## Workflow

### Step 1: Clarify the Research Question
Before searching, confirm with the user:
1. What specific claim or gap are we investigating?
2. What time range? (default: 2023+ for fast-moving fields)
3. Any must-include or must-exclude papers?
4. Need venue/conference filtering?

### Step 2: Generate Query Variants
Create 3–5 search queries covering different angles:
- Technical terms → `--source all`
- Application domain → `--source crossref` (good venue metadata)
- Key author → `--source openalex --author "Name"`
- Conference-specific → `--source openalex --venue "NeurIPS"`

### Step 3: Execute Search
Run searches, starting with `--source all --dedup`:
```bash
python $SCRIPT --source all "QUERY" --dedup --limit 10 --compact --year-from 2023
```
If S2 rate-limited (429), the other 3 sources still return results.

For web-level queries (finding proceedings, author pages, blog posts):
```bash
python $SCRIPT --source ddg "QUERY" --limit 5 --compact
```

### Step 4: Screen & Rank
Present results as a candidate table:
| # | Title | Year | Venue | Cites | Rank | Why relevant |
|---|-------|------|-------|-------|------|-------------|

Ranking priority: relevance to question > citation count > recency.

### Step 5: Deep Read (A-rank papers)
For top papers, fetch details and generate a card:
```bash
python $SCRIPT --paper "PAPER_ID" --save-card
```
For arXiv papers, read full text via Playwright:
```
browser_navigate: https://arxiv.org/html/ARXIV_ID
```

### Step 6: Evidence Annotation
After reading, annotate each paper with:
- What claim it supports / challenges
- Reusable methods, datasets, evaluation protocols
- Limitations and follow-up papers

## Note Governance

### Why Governance Matters
45+ notes with inconsistent formats → impossible to navigate, review, or build upon.
Standardized format from the start means every note is immediately useful.

### Paper Note Naming Convention
```
KC-{TOPIC-SLUG}.md
```
- `KC-` prefix for all paper notes
- Topic slug: UPPER-CASE, hyphenated, descriptive (e.g., `KC-FORMAL-ONTOLOGY-GUARINO`)
- Stored in `literature/paper-notes/`
- Register in `literature/README.md` index immediately after creation

### Mandatory Paper Note Template
Every paper note MUST have these sections:

```markdown
# [Descriptive Title in Chinese or English]

> **收藏日期**: YYYY-MM-DD
> **来源**: Full citation (authors, year, title, venue)
> **DOI / arXiv**: identifiers
> **引用数**: N (source)
> **相关性**: 🔴核心 / 🟡重要 / 🟢参考 — [one-line why]
> **升级路线**: Stage A1/A2/A3/A4 or "竞争态势" or "支撑"

## 核心摘要
[2-3 sentences: what this paper does and why it matters]

## 关键内容
### [Section as appropriate to the paper]

## 对本研究的价值
- **直接支持**: [specific claim or design decision]
- **可复用概念**: [reusable ideas, methods, definitions]
- **挑战/质疑**: [anything that contradicts our approach]

## 后续追踪
- [ ] [follow-up papers or verification needed]
```

### Format Rules
1. **Language**: Chinese for narrative sections, English for citations/code/terms
2. **Metadata block**: Always include the 5-line header (日期/来源/DOI/引用数/相关性)
3. **Relevance tagging**: Use emoji 🔴🟡🟢 to indicate importance, always explain why
4. **Cross-references**: Link related notes with `[KC-XXX](KC-XXX.md)`
5. **No orphan notes**: Every new note MUST be registered in `literature/README.md`
6. **No empty stubs**: If a note is created, fill at least 核心摘要 + 对本研究的价值

### Content Categories
When registering in the index, classify by:
- **Stage A1**: Formal Ontology / Knowledge Representation
- **Stage A2**: Provenance / Artifact Standards
- **Stage A3**: Evaluation Methodology
- **Stage A4**: RS Agent Differentiation
- **竞争态势**: Competing research lines
- **Scientific Agents**: Agent systems analysis
- **Knowledge Engineering**: KG construction, knowledge injection, ontology engineering
- **其他**: Tools, methods, misc

### Lifecycle
1. **Created** during search sprint → fill template + register in index
2. **Enriched** during deep read → add 对本研究的价值, cross-references
3. **Synthesized** during upgrade planning → extract into `thinking-space/` design docs
4. **Archived** if superseded → mark as `[SUPERSEDED]` in index, don't delete
Each card follows this structure (auto-generated with `--save-card`):
```markdown
# [Paper Title]
> Date | Source | Venue | Year | DOI | arXiv | Citations
## Core Summary
## Research Problem
## Method
## Data & Evaluation
## Key Findings
## Limitations
## Relevance to [User's Research]
## Follow-up Papers
## Citation Risk
```

## Rules
1. Never invent citations, DOIs, datasets, or experimental results.
2. Mark uncertain metadata as `[NEEDS VERIFICATION]`.
3. Separate: verified evidence | plausible inference | open question | speculative idea.
4. Prefer primary sources (papers, official docs) over blog summaries.
5. For each paper, extract: task, data, method, evaluation, limitation, relevance.
6. Rate relevance conservatively.
7. Keep a search log showing what was queried and what was found.
8. When S2 is 429'd, rely on OpenAlex + Crossref + arXiv (all unlimited).
9. Use Playwright for Semantic Scholar web when API search misses relevant papers.
10. Never use Google Scholar via Playwright (blocked by anti-bot).

## Output
Every sprint produces:
1. **Search log** (queries, sources, hit counts)
2. **Candidate table** (screened and ranked)
3. **Paper cards** (for A-rank papers)
4. **Next actions** (what to verify, read next, still uncertain)

## Search Session Log

### Why Log
Search logs serve three purposes:
1. **复盘** — reconstruct what was searched, what worked, what missed
2. **可复现** — another agent can replay the same search pipeline
3. **知识积累** — successful search strategies become reusable patterns

### Two-Layer Logging

**Layer 1: CLI logs (automatic)**

Add `--log-dir ./search-logs` to any command. Each call appends a JSON line:
```bash
python $SCRIPT --source all "query" --dedup --log-dir ./search-logs --compact
```
Log format (`search-YYYY-MM-DD.jsonl`):
```json
{"timestamp": "2026-06-10T14:30:00", "action": "search", "params": {"query": "...", "source": "all", ...}, "results": {"total_raw": 12, "total_deduped": 8, "top3": ["Paper A", "Paper B", "Paper C"]}}
```

**Layer 2: Session narrative (agent writes)**

At the end of each sprint, generate a markdown session log:
```markdown
# Search Session: [TOPIC]
> Date: YYYY-MM-DD | Goal: [what are we trying to find]

## Research Question
[The specific claim or gap being investigated]

## Search Strategy
[Why these tools/queries were chosen — the thinking process]

## Actions
| # | Action | Tool | Query/Params | Hits | Notes |
|---|--------|------|-------------|------|-------|
| 1 | Broad scan | --source all | "formal ontology Guarino" | 9 | S2 429'd, Crossref found key 1995 paper |
| 2 | Narrow by venue | --source openalex --venue AAAI | "knowledge graph" | 5 | Found KG-Agent paper |
| 3 | Paper detail | --paper ArXiv:xxxx | — | 1 | Fell back to OpenAlex DOI |

## Key Findings
- [Finding 1 with citation]
- [Finding 2 with citation]

## What Worked
- [Strategy that produced good results]

## What Missed
- [Query that returned irrelevant results, and why]

## Next Steps
- [What to search next, different angle to try]
```

Save session logs to the project's `thinking-space/` or `search-logs/` directory.

## Changelog

### v0.2 (2026-06-10) — Search Matrix Expansion
- Added Crossref API as 4th academic source
- Added DuckDuckGo general web search (`--source ddg`)
- Added `--venue` filter with conference aliases (neurips, aaai, kdd, etc.)
- Added `--author` filter (OpenAlex, Crossref)
- Fixed OpenAlex NoneType crash (defensive `_safe_get()`)
- Fixed arXiv query format (removed `all:` prefix)
- Fixed `--paper` to multi-source fallback (S2 → Crossref → OpenAlex DOI)
- Added OpenAlex arXiv ID extraction from DOI/landing_page_url
- Fixed Windows console encoding (UTF-8 reconfigure)
- Added Playwright MCP integration for browser-based search
- Confirmed: Google Scholar blocks Playwright; Semantic Scholar web works perfectly

### v0.1 (2026-06-10) — Initial Release
- Three academic sources: S2, arXiv, OpenAlex
- Cross-source dedup by DOI/arXiv ID
- Citation graph traversal
- Paper card generation
- Zero mandatory dependencies

## Reference Classification (引用分级)

### Why Classification Matters
Not all references deserve the same depth of treatment. Classification ensures PRIMARY papers get deep analysis while BACKGROUND papers get just enough coverage.

### Three Tiers

| Level | Mark | Criteria | Paper Note Depth | RW Treatment |
|-------|------|----------|-----------------|-------------|
| 🔴 PRIMARY | Core reference | Research question highly overlaps + strong workflow reference + top-venue published | **Full**: abstract + method + experiments + detailed diff table + BibTeX | Detailed comparison paragraph + differentiation table |
| 🟡 SECONDARY | Important auxiliary | Methodology support / competitive positioning / evaluation reference | **Standard**: abstract + key method + value to our work + BibTeX | Cited in subsection, not detailed |
| 🟢 BACKGROUND | Background | Domain common knowledge / historical reference | **Minimal**: 2-3 sentences + BibTeX | One sentence mention |

### PRIMARY Selection Rules
1. **≤ 5 papers** total. If you have more, some should be SECONDARY.
2. Must satisfy ALL three: (a) research question highly overlaps with ours, (b) work style has strong reference value, (c) top-venue formally published.
3. These are the papers you must "eat through" — read every section, understand every experiment, compare every design choice.

### Classification Workflow
After each search sprint:
1. Screen candidates by relevance
2. Classify each paper into PRIMARY / SECONDARY / BACKGROUND
3. Allocate reading time accordingly: PRIMARY = full text, SECONDARY = abstract + key sections, BACKGROUND = abstract only

## Search Improvement Log

### Lessons Learned (2026-06-10)

**Missing papers and why**:
- Way to Specialist (KDD 2025) missed because queries focused on "knowledge governance + evidence + asset" but not "evolving domain KG"
- AriGraph (IJCAI 2025) missed because no "graph memory agent" query variant
- ScienceAgentBench venue (ICLR 2025) missed because S2 venue field didn't show it — needed OpenReview verification

**Improvements to apply**:
1. After finding a key paper, run `--citations` and `--references` to trace citation graph
2. Use query variants across three dimensions: domain keywords + method keywords + evaluation keywords
3. Venue verification priority: OpenReview > Semantic Scholar > OpenAlex > Crossref
4. After search completion, do a "gap check": scan citations in existing notes for missed PRIMARY-level papers
