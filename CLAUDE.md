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

Start the knowledge acquisition pipeline:
```bash
# Trigger full pipeline run
claude --prompt "Run knowledge acquisition pipeline"

# Run specific stage
claude --prompt "Run Scout stage"
claude --prompt "Run Extractor stage"
```

Inspect pipeline status:
```bash
# Check last run timestamp
cat sources/.last-run

# View pending changes
git diff knowledge/
```
