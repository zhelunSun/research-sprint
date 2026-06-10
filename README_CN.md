# Research Sprint

终端里跑的学术文献搜索。三个数据库，零配置，不需要 API Key。

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![No Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

---

## 一句话

```bash
python academic_search.py --source all "本体增强的RAG" --dedup --limit 10 --compact
```

同时搜索 Semantic Scholar、arXiv、OpenAlex。按 DOI 和 arXiv ID 去重。输出排序好的表格。完事。

不需要 pip install。不需要 API Key。不需要配置文件。Python 3.8 标准库就够了。

## 什么时候用它

**适合用**：你想从脚本、Claude Code 或任何 LLM Agent 调用学术搜索，要的是结构化输出（论文卡片、引用图谱、JSON），不是聊天摘要。

**用 [paper-search-mcp](https://github.com/nicepkg/paper-search-mcp)**：如果你想要一个 MCP Server，搜索 20+ 数据源，能下载 PDF。它覆盖面更广；Research Sprint 在少量数据源上做得更深（引用图谱 + 论文卡片）。

**用 [ScholarAI](https://scholar.ai/)**：如果你想要一个好看的 Web 界面做可视化探索。它做得很好，但是收费 SaaS。

| | Research Sprint | paper-search-mcp | ScholarAI |
|---|---|---|---|
| 数据源 | S2 + arXiv + OpenAlex | 20+ | 多源 |
| 引用图谱 | 前向 + 后向 | 无 | 部分 |
| 论文卡片 | 结构化 Markdown | 无 | 无 |
| 去重 | 跨源 | 有 | 无 |
| 依赖 | 零 | Python + MCP | 浏览器 |
| 费用 | 免费 | 免费 | 免费增值 |

Research Sprint 用数据源数量换深度。三个源对大多数 CS/AI 研究够了；价值在引用图谱和结构化卡片，不在数据库数量。

## 快速开始

```bash
git clone https://github.com/zhelunSun/research-sprint.git
cd research-sprint

# 三源联合搜索
python scripts/academic_search.py --source all "遥感智能体" --dedup --limit 10 --compact

# 获取论文详情
python scripts/academic_search.py --paper "ArXiv:2409.13731"

# 谁引用了这篇论文？
python scripts/academic_search.py --citations "ArXiv:2409.13731" --limit 5

# 这篇论文引用了什么？
python scripts/academic_search.py --references "ArXiv:2409.13731" --limit 5

# 生成论文卡片（用于知识库）
python scripts/academic_search.py --source s2 "知识图谱 智能体" --limit 5 --save-card

# JSON 输出（用于流水线）
python scripts/academic_search.py --source all "RAG 本体" --json --year-from 2024
```

## Claude Code 集成

```bash
cp -r claude-code/ ~/.claude/skills/research-sprint/
# 编辑 SKILL.md — 把 <REPO_PATH> 替换成你的克隆路径
```

Claude Code 会自动处理完整的研究流程：明确问题 → 生成查询变体 → 搜索 → 筛选排序 → 深度阅读 → 标注。

## 可选加速

不加 Key 也能跑。加上只是更快：

```bash
# Semantic Scholar — 免费 Key，速率从 1/s 提升到 10/s
# 申请: https://www.semanticscholar.org/product/api
export S2_API_KEY="your-key"

# OpenAlex 礼貌池 — 随便填个邮箱就行
export OPENALEX_EMAIL="you@university.edu"
```

## 设计

一个 Python 文件。没有框架。`urllib` + `json` + `xml.etree` 覆盖三个 API。这是特性，不是缺陷——意味着在任何 Python 环境都能用，包括不能 pip install 的 conda/venv。

## 数据源

| 数据源 | 搜索 | 详情 | 引用 | 速率限制 |
|--------|------|------|------|----------|
| Semantic Scholar | ✅ | ✅ | 前向 + 后向 | ~1/s（有 Key 10/s） |
| arXiv | ✅ | — | — | ~1/s |
| OpenAlex | ✅ | — | — | ~10/s |

## 许可证

[MIT](LICENSE) — 随便用。

数据来自 [Semantic Scholar](https://www.semanticscholar.org/)、[arXiv](https://arxiv.org/)、[OpenAlex](https://openalex.org/)。
