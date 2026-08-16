# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Scope

Autonomous Knowledge Acquisition System for Amazon Ads content. Continuously discovers, extracts, validates, and merges knowledge into a structured knowledge base.

## Pipeline

**Discover → Extract → Validate → Merge → Publish**

- Must be safe to re-run (no duplicates, only real changes applied)
- Detect changes using content hashes, update only affected documents

## Output Format

**Google's OKF (Open Knowledge Format)**
- Markdown files with frontmatter metadata
- Stored in `knowledge/` directory
- One document per topic (deduplicate/merge facts from multiple sources)

## Source Types

1. **Amazon Ads official help docs** (highest priority)
2. **GitHub repos** related to Amazon Ads API/MCP
3. **Blog posts** about Amazon Ads

## Requirements

**Every fact must include:**
- Source URL (traceable)
- Confidence level: `high` | `medium` | `low`
- Source type: `official` | `community` | `blog`

**Conflict resolution:**
- Prefer official sources over community/blog
- Note conflicts in document metadata

**Re-run safety:**
- Content hashes detect what changed since last run
- Only update documents with actual changes
- Never duplicate entries

## Architecture

**Subagents** (`.claude/agents/`):
- `Scout` — discover sources
- `Extractor` — pull facts from sources
- `Validator` — check against existing knowledge
- `Merger` — combine facts into OKF documents

**Skills** (`.claude/skills/`):
- OKF formatting rules
- Deduplication rules
- Citation rules

**Hook** (`.claude/settings.json`):
- Pre-write validation hook (validates OKF format before writing files)

## Folder Structure

```
amazon-ads-kb/
├── .claude/
│   ├── agents/          # Subagent definitions
│   ├── skills/          # Skill definitions
│   └── settings.json    # Hooks and configuration
├── knowledge/           # OKF documents (output)
└── sources/             # Discovered source URLs/metadata
```

## Running the Pipeline

`scripts/pipeline.py` is the orchestrator — it runs deterministic stages
(fetch, hash, write) directly and shells out to `claude` for the fuzzy stages
(extraction, validation, topic assignment), using the subagent definitions in
`.claude/agents/`:

```bash
# Trigger full pipeline run
python scripts/pipeline.py --config sources/seed-urls.json

# Single source
python scripts/pipeline.py --url "https://advertising.amazon.com/solutions/products/sponsored-products" --type official
```

There is no `claude --prompt` flag — `claude`'s non-interactive flag is
`-p`/`--print`, and `scripts/pipeline.py` calls it directly via `subprocess`
(see `_invoke_claude_agent`), rather than a human typing a prompt into the
CLI stage by stage.

Inspect pipeline status:
```bash
# Every run appends a real entry here (written by code, not by hand)
tail -40 knowledge/log.md

# Per-source hash/fetch history
cat sources/sources.json

# View pending changes
git diff knowledge/
```
