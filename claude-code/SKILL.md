# Research Sprint — Academic Literature Search & Structured Evidence Capture

## Trigger
When the user mentions any of: "research sprint", "lit search", "find papers", "literature review", "paper search", "evidence map", "gap map", "search papers", "文献搜索", "文献调研", "找论文".

## Overview
A structured academic research workflow. Searches Semantic Scholar, arXiv, and OpenAlex (all free APIs), then produces ranked candidate tables, structured paper cards, and evidence annotations — designed for researchers who need traceable, auditable literature pipelines rather than one-shot summaries.

## Prerequisites
- Python 3.8+ (no external dependencies)
- Optional: `S2_API_KEY` env var for faster Semantic Scholar access

## Core Tool
```bash
SCRIPT="<REPO_PATH>/scripts/academic_search.py"
```
Replace `<REPO_PATH>` with the absolute path to this skill's repo (e.g. `D:/Projects/skills/research-sprint`).

### Available Commands
```bash
# Multi-source search with deduplication
python $SCRIPT --source all "query" --dedup --limit 10 --compact

# Single source
python $SCRIPT --source s2 "query" --limit 10 --compact
python $SCRIPT --source arxiv "query" --limit 10 --compact
python $SCRIPT --source openalex "query" --limit 10 --compact

# Paper details (by S2 ID, DOI, or arXiv ID)
python $SCRIPT --paper "ArXiv:2409.13731"
python $SCRIPT --paper "DOI:10.1145/3701716.3715240"

# Citation graph traversal
python $SCRIPT --citations "PAPER_ID" --limit 10
python $SCRIPT --references "PAPER_ID" --limit 10

# Generate paper card markdown
python $SCRIPT --source s2 "query" --limit 5 --save-card

# JSON output for pipelines
python $SCRIPT --source all "query" --json
```

## Workflow

### Step 1: Clarify the Research Question
Before searching, confirm with the user:
1. What specific claim or gap are we investigating?
2. What time range? (default: 2023+ for fast-moving fields)
3. Any must-include or must-exclude papers?

### Step 2: Generate Query Variants
Create 3–5 search queries covering different angles:
- Technical terms
- Application domain
- Method class
- Key author / citation chain

### Step 3: Execute Search
Run searches, starting with `--source all --dedup`:
```bash
python $SCRIPT --source all "QUERY" --dedup --limit 10 --compact --year-from 2023
```
If S2 rate-limited (429), fall back to `--source arxiv` and `--source openalex` separately.

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
Or use `web_reader` to fetch the full arXiv page for deeper reading.

### Step 6: Evidence Annotation
After reading, annotate each paper with:
- What claim it supports / challenges
- Reusable methods, datasets, evaluation protocols
- Limitations and follow-up papers

## Paper Card Template
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

## Output
Every sprint produces:
1. **Search log** (queries, sources, hit counts)
2. **Candidate table** (screened and ranked)
3. **Paper cards** (for A-rank papers)
4. **Next actions** (what to verify, read next, still uncertain)
