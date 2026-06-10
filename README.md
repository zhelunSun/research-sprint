# Research Sprint 🚀

> **Zero-config academic literature search for AI-powered research workflows.**
> One command to search 3 databases, deduplicate, and generate structured paper cards.

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![No Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

---

## What It Does

**For researchers using Claude Code** — turns your AI coding assistant into a structured literature review engine:

```
You: "Find me papers on ontology-grounded retrieval augmented generation"

→ Searches Semantic Scholar + arXiv + OpenAlex
→ Deduplicates by DOI/arXiv ID
→ Ranks by relevance & citations
→ Generates structured paper cards ready for your knowledge base
```

### Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **3-database search** | Semantic Scholar, arXiv, OpenAlex — all free APIs |
| 🔗 **Citation graph** | Forward citations + backward references traversal |
| 🧹 **Auto dedup** | Cross-source deduplication by DOI and arXiv ID |
| 📋 **Paper cards** | Structured markdown templates for knowledge management |
| 🚫 **Zero dependencies** | Pure Python stdlib — no pip install needed |
| 🔑 **Optional API keys** | Works without keys; faster with free S2 API key |
| 🤖 **Claude Code Skill** | Drop-in skill with full research workflow |

### How It Compares

| | Research Sprint | paper-search-mcp | ScholarAI | Manual Search |
|---|---|---|---|---|
| **Data sources** | S2 + arXiv + OpenAlex | 20+ | Multi | One at a time |
| **Citation graph** | ✅ forward + backward | ❌ | ✅ | Manual |
| **Paper cards** | ✅ structured markdown | ❌ | ❌ | Manual |
| **Deduplication** | ✅ cross-source | ✅ | ❌ | Manual |
| **Dependencies** | Zero | Python + MCP | Paid API | — |
| **Cost** | Free forever | Free | Freemium | Free |

## Quick Start

### Option 1: Claude Code Skill (recommended)

```bash
# Clone
git clone https://github.com/YOUR/research-sprint.git ~/.claude/skills/research-sprint

# Edit SKILL.md — replace <REPO_PATH> with your clone path
# Done! Next Claude Code session will auto-detect research queries.
```

### Option 2: Standalone CLI

```bash
# No install needed
python scripts/academic_search.py --source all "knowledge graph agent" --dedup --limit 10 --compact
```

### Option 3: Install globally

```bash
# Add to PATH or alias
echo 'alias research="python /path/to/research-sprint/scripts/academic_search.py"' >> ~/.bashrc
```

## Usage Examples

```bash
# Multi-source search with dedup
python scripts/academic_search.py --source all "evidence governance knowledge" --dedup --limit 5

# Targeted search
python scripts/academic_search.py --source s2 "RAG ontology reasoning" --limit 10 --year-from 2024
python scripts/academic_search.py --source arxiv "remote sensing agent" --limit 10 --compact

# Get paper details
python scripts/academic_search.py --paper "ArXiv:2409.13731"

# Citation graph — who cited this paper?
python scripts/academic_search.py --citations "ArXiv:2409.13731" --limit 5

# What does this paper reference?
python scripts/academic_search.py --references "ArXiv:2409.13731" --limit 5

# Generate paper cards for knowledge base
python scripts/academic_search.py --source s2 "query" --limit 5 --save-card

# JSON output for pipelines
python scripts/academic_search.py --source all "query" --json --year-from 2023
```

## Optional Configuration

```bash
# Semantic Scholar API key — free, improves rate limit from ~1/s to ~10/s
# Apply at: https://www.semanticscholar.org/product/api
export S2_API_KEY="your-key-here"

# OpenAlex polite pool — any email works
export OPENALEX_EMAIL="you@university.edu"
```

## Architecture

```
research-sprint/
├── claude-code/
│   └── SKILL.md              # Claude Code skill definition
├── scripts/
│   └── academic_search.py    # Core search engine (zero deps)
├── tests/
│   └── test_search.py        # Basic tests
├── ROADMAP.md                # Future plans & design notes
├── README.md
└── LICENSE
```

### Design Principles

1. **Zero dependencies first** — stdlib only, works in any Python 3.8+ environment
2. **Free-first APIs** — all sources are free; keys are optional and only improve rate limits
3. **CLI as universal interface** — any tool can call it via `subprocess`
4. **Unified schema** — all sources normalized to the same output fields
5. **Citation as first-class** — forward/backward traversal is a core feature, not an add-on

## Data Sources

| Source | Search | Details | Citations | PDF | Rate Limit |
|--------|--------|---------|-----------|-----|------------|
| Semantic Scholar | ✅ | ✅ | ✅ | ✅ (OA) | ~1/s (10/s with key) |
| arXiv | ✅ | — | — | ✅ | ~1/s |
| OpenAlex | ✅ | — | — | — | ~10/s |

## Use Cases

- **PhD literature reviews** — systematic search → structured paper cards → evidence matrix
- **Research sprint workflows** — Claude Code + this skill = AI research assistant
- **Citation chain discovery** — find who cited a key paper, explore research lineages
- **Cross-source verification** — same query across 3 databases, deduplicated

## License

MIT — use it, fork it, share it.

## Acknowledgments

Built for the [Claude Code](https://docs.anthropic.com/en/docs/claude-code) ecosystem. Data provided by [Semantic Scholar](https://www.semanticscholar.org/), [arXiv](https://arxiv.org/), and [OpenAlex](https://openalex.org/).
