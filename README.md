# Research Sprint

Academic literature search that runs in your terminal. Three databases, zero config, no API keys required.

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![No Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

---

## what it does

```
python academic_search.py --source all "ontology-grounded RAG" --dedup --limit 10 --compact
```

That one line hits Semantic Scholar, arXiv, and OpenAlex. Deduplicates by DOI and arXiv ID. Prints a ranked table. Done.

No pip install. No API keys. No config files. Python 3.8 stdlib only.

## when to use this (and when not to)

**Use this if** you want a CLI you can call from scripts, Claude Code, or any LLM agent — and you want structured output (paper cards, citation graphs, JSON) rather than a chat summary.

**Use [paper-search-mcp](https://github.com/nicepkg/paper-search-mcp) if** you want an MCP server that searches 20+ sources and downloads PDFs. It covers more sources; Research Sprint adds citation traversal and paper cards on top of a smaller source set.

**Use [ScholarAI](https://scholar.ai/) if** you want a web UI with visual exploration. It's polished, but it's a paid SaaS.

| | Research Sprint | paper-search-mcp | ScholarAI |
|---|---|---|---|
| Sources | S2 + arXiv + OpenAlex | 20+ | Multi |
| Citation graph | forward + backward | no | partial |
| Paper cards | structured markdown | no | no |
| Dedup | cross-source | yes | no |
| Dependencies | zero | Python + MCP | browser |
| Cost | free | free | freemium |

Research Sprint trades source count for depth. Three sources is enough for most CS/AI research; the value is in the citation graph and the structured cards, not the number of databases.

## quick start

```bash
# Clone and run — nothing else to install
git clone https://github.com/zhelunSun/research-sprint.git
cd research-sprint

# Search all three databases
python scripts/academic_search.py --source all "remote sensing agent" --dedup --limit 10 --compact

# Get paper details
python scripts/academic_search.py --paper "ArXiv:2409.13731"

# Who cited this paper?
python scripts/academic_search.py --citations "ArXiv:2409.13731" --limit 5

# What does this paper reference?
python scripts/academic_search.py --references "ArXiv:2409.13731" --limit 5

# Generate paper cards for your knowledge base
python scripts/academic_search.py --source s2 "knowledge graph agent" --limit 5 --save-card

# JSON output for pipelines
python scripts/academic_search.py --source all "RAG ontology" --json --year-from 2024
```

## claude code skill

If you use Claude Code, drop the skill into your skills directory:

```bash
cp -r claude-code/ ~/.claude/skills/research-sprint/
# Edit SKILL.md — replace <REPO_PATH> with your clone path
```

Then Claude Code will handle the full research workflow: clarify question → generate query variants → search → screen & rank → deep read → annotate.

## optional: faster searches

Everything works without keys. These just make it faster:

```bash
# Semantic Scholar — free key, bumps rate limit from 1/s to 10/s
# Apply at: https://www.semanticscholar.org/product/api
export S2_API_KEY="your-key"

# OpenAlex polite pool — any email works
export OPENALEX_EMAIL="you@university.edu"
```

## architecture

```
research-sprint/
├── claude-code/
│   └── SKILL.md              # Claude Code skill definition
├── scripts/
│   └── academic_search.py    # Core search engine (~500 lines, zero deps)
├── tests/
│   └── test_search.py
├── ROADMAP.md
├── README.md
└── LICENSE                   # MIT
```

One Python file. No framework. `urllib` + `json` + `xml.etree` cover all three APIs. This is a feature, not a limitation — it means the tool works in any Python environment, including locked-down conda/venv setups where you can't pip install anything.

## data sources

| Source | Search | Details | Citations | Rate limit |
|--------|--------|---------|-----------|------------|
| Semantic Scholar | yes | yes | forward + backward | ~1/s (10/s with key) |
| arXiv | yes | — | — | ~1/s |
| OpenAlex | yes | — | — | ~10/s |

## license

[MIT](LICENSE) — use it, fork it, share it.

Built for the [Claude Code](https://docs.anthropic.com/en/docs/claude-code) ecosystem. Data from [Semantic Scholar](https://www.semanticscholar.org/), [arXiv](https://arxiv.org/), and [OpenAlex](https://openalex.org/).
