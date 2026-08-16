# Amazon Ads Knowledge Base

Autonomous knowledge acquisition system for Amazon Ads content. Continuously discovers, extracts, validates, and merges knowledge into a structured knowledge base using Open Knowledge Format (OKF).

## 🎯 What This Project Does

This system automatically builds and maintains a comprehensive knowledge base about Amazon Ads by:

1. **Discovering** relevant sources (official docs, GitHub repos, blog posts)
2. **Extracting** factual claims from each source
3. **Validating** facts against existing knowledge (detecting duplicates, conflicts, new info)
4. **Merging** validated facts into structured OKF documents
5. **Publishing** updated knowledge base with proper attribution

### Key Features

- **Re-run Safe**: Content hashing prevents duplicate processing
- **Conflict Resolution**: Automatic resolution based on source confidence (official > community > blog)
- **Proper Attribution**: Every fact cites its source with confidence levels
- **Incremental Updates**: Only processes changed content
- **Quality Controlled**: Pre-write validation ensures OKF compliance

## 📋 Prerequisites

### Required Software

- **Node.js** (v16+) - Runs `scripts/validate-okf.js`, the OKF format hook
- **Python** (v3.8+) - Runs `scripts/pipeline.py`, the orchestrator
- **Git** - For version control
- **Claude Code CLI** - `claude` must be on your PATH and logged in; the pipeline shells out to it for extraction, validation, and topic-assignment (see `_invoke_claude_agent` in `scripts/pipeline.py`)

### Python dependencies

```bash
pip install -r requirements.txt
```

There is no `package.json` — nothing here is an npm package. `node` is only
used to run `scripts/validate-okf.js` directly (`node scripts/validate-okf.js`),
not as part of any Node build/install step.

Content fetching is done with the Python `requests` + `beautifulsoup4`
libraries directly (see `fetch_content()` in `scripts/pipeline.py`) — there
is no MCP server (Playwright, web-reader, or otherwise) in the fetch path.
If you want to swap in an MCP-based fetcher later, `fetch_content()` is the
single place to change.

## 🚀 Setup Steps

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd amazon-ads-kb
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Log in to Claude Code

```bash
claude /login
```

The pipeline calls `claude -p ... --agent <name> --agents <custom-def> --output-format json --json-schema <schema>` per source (see `_invoke_claude_agent`). If you're on a proxied endpoint (e.g. a LiteLLM gateway) rather than api.anthropic.com directly, copy `.claude/settings.json.example`'s `env` block into `.claude/settings.local.json` and fill in your token — don't put real tokens in `.claude/settings.json`, it's committed.

### Step 4: Verify Setup

```bash
# Check that required files exist
ls .claude/agents/
ls .claude/skills/
ls scripts/
ls sources/

# Test hash check script
python scripts/hash_check.py "https://example.com" "test content"
# Should return: "new"

# Test OKF validation directly (the hook receives this same JSON shape on stdin)
echo '{"tool_name":"Write","tool_input":{"file_path":"knowledge/x.md","content":"---\ntitle: \"X\"\nlast_updated: 2026-01-01T00:00:00Z\ntype: knowledge\nsources:\n  - url: \"https://example.com\"\n    type: official\n    confidence: high\n---\n\nbody"}}' | node scripts/validate-okf.js; echo "exit: $?"
# Should print nothing and exit 0 (valid). Drop the "type:" line to see exit 2 + a JSON denial reason.
```

### Step 5: Configure Seed URLs (Optional)

Edit `sources/seed-urls.json` with your desired Amazon Ads sources:

```json
{
  "seeds": [
    {
      "url": "https://advertising.amazon.com/help",
      "source_type": "official",
      "description": "Amazon Ads official Help Center",
      "enabled": true
    }
  ]
}
```

## ▶️ How to Run the Pipeline

### First Run (Initial Knowledge Base Creation)

```bash
# Run the full pipeline with default seed URLs
python scripts/pipeline.py --config sources/seed-urls.json

# Or run with a single source
python scripts/pipeline.py --url "https://advertising.amazon.com/help" --type official
```

**What happens during first run:**
1. ✅ Discovers sources from seed URLs
2. ✅ Fetches content from each URL
3. ✅ Extracts factual claims
4. ✅ Validates against existing knowledge (all will be "new" first run)
5. ✅ Creates OKF documents in `knowledge/`
6. ✅ Updates index and log files

### Subsequent Runs (Incremental Updates)

```bash
# Run pipeline again - automatically detects changes via hash checking
python scripts/pipeline.py --config sources/seed-urls.json
```

**What happens during re-runs:**
1. ✅ Checks content hashes against stored values
2. ✅ Skips unchanged sources (efficient processing)
3. ✅ Only processes sources with new content
4. ✅ Updates existing documents if needed
5. ✅ Logs all changes made

**Expected time:**
- First run: 5-10 minutes (depending on number of sources)
- Re-run (no changes): <1 minute (hash checking only)
- Re-run (1 source changed): 2-3 minutes (incremental processing)

## 📁 Folder Structure

```
amazon-ads-kb/
├── .claude/
│   ├── agents/              # Claude subagent definitions
│   │   ├── scout.md        # Source discovery agent
│   │   ├── extractor.md    # Fact extraction agent
│   │   ├── validator.md    # Fact validation agent
│   │   └── merger.md       # Document merging agent
│   ├── skills/              # Reusable skill definitions
│   │   ├── okf-format.md   # OKF v0.1 specification
│   │   ├── dedup-rules.md  # Deduplication rules
│   │   └── citation-rules.md # Citation guidelines
│   └── settings.json        # Claude Code settings (hooks, permissions)
├── knowledge/               # Generated OKF documents
│   ├── index.md            # Topic index and statistics
│   ├── log.md              # Pipeline changelog
│   └── *.md                # OKF documents (auto-generated)
├── sources/                 # Source configuration and tracking
│   ├── seed-urls.json      # Initial source URLs
│   └── sources.json        # Source hash database (auto-updated)
├── scripts/                 # Automation scripts
│   ├── pipeline.py         # Main pipeline orchestration
│   ├── hash_check.py       # Content hash checking
│   └── validate-okf.js     # OKF format validation
└── README.md               # This file
```

## ✅ How to Verify It Worked

### 1. Check Knowledge Directory File Count

```bash
# List files in knowledge directory
ls knowledge/

# knowledge/ always contains index.md + log.md plus one .md per topic.
# Count topic documents (excludes index.md and log.md):
ls knowledge/*.md | grep -v -e index.md -e log.md | wc -l
```

### 2. Verify Document Quality

```bash
# Check that documents have proper OKF format
head -15 knowledge/amazon-ads-help-center.md

# Should show YAML frontmatter with:
# ---
# title: "Document Title"
# last_updated: 2026-08-10T12:00:00Z
# sources:
#   - url: "https://..."
#     type: official
#     confidence: high
# topic_id: document-slug
# ---
```

### 3. Check Knowledge Index

```bash
# View the knowledge base index
cat knowledge/index.md

# Should show table with:
# - Topic titles, filenames, last updated dates, source counts
# - Statistics section with total documents and sources
# - Category index with document listings
```

### 4. Review Pipeline Log

```bash
# Check the pipeline run log
tail -50 knowledge/log.md

# Every entry is written by _write_summary() in scripts/pipeline.py, in this
# exact format — if you ever see an entry that doesn't look like this, it
# was added by hand, not by the pipeline:
# ## Pipeline Run: 2026-08-16T12:00:00Z
#
# **Duration**: 12.34 seconds
# **Sources Processed**: 2
# **Sources Skipped**: 1
# **Sources Failed**: 0
#
# **Statistics**:
# - Facts extracted: 9
# - Facts new: 7
# ...
```

### 5. Verify Hash Tracking

```bash
# Check that sources are being tracked
cat sources/sources.json

# Should contain entries for each processed source with:
# - content_hash (SHA-256 hash)
# - last_checked (ISO timestamp)
# - last_changed (ISO timestamp)  
# - source_type (official/community/blog)
# - fetch_count and change_count
```

### 6. Test Re-run Safety

```bash
# Run pipeline again immediately
python scripts/pipeline.py --config sources/seed-urls.json

# Check log - should show "Sources skipped: 3" or similar
# File count in knowledge/ should remain the same
tail -20 knowledge/log.md
```

## 🔍 Troubleshooting

### Agent stages return nothing / pipeline falls back to deterministic extraction every time

**Problem**: Log shows `Extractor agent failed, using fallback extraction` (or validator/merger equivalents) on every run.

**Solution**:
```bash
# Confirm claude is on PATH and logged in
claude -p "say ok" --output-format json
# is_error should be false; if it says "Not logged in", run: claude /login

# Confirm the agent definition loads
cat .claude/agents/extractor.md
```
The fallback exists so a broken `claude` install doesn't stop the pipeline —
but if you only ever see fallback-quality facts, this is why. It is NOT
silent: every fallback is logged.

### Hash Check Script Fails

**Problem**: `python scripts/hash_check.py` returns errors

**Solution**:
```bash
# Verify Python version (3.8+)
python --version

# Test hash check manually
python scripts/hash_check.py "https://example.com" "test"
# Should return: "new"
```

### No Documents Created

**Problem**: Pipeline runs but knowledge/ directory stays empty

**Solution**:
```bash
# Check pipeline output for errors
python scripts/pipeline.py --config sources/seed-urls.json 2>&1 | tee pipeline.log

# Verify seed URLs configuration
cat sources/seed-urls.json

# Test with single source first
python scripts/pipeline.py --url "https://advertising.amazon.com/help" --type official
```

### OKF Validation Errors

**Problem**: Documents rejected during merge stage

**Solution**: Check that documents have required frontmatter:
```yaml
---
title: "Document Title"
last_updated: 2026-08-10T12:00:00Z
sources:
  - url: "https://..."
    type: official
    confidence: high
topic_id: document-slug
---
```

## 📊 Expected Pipeline Performance

| Scenario | Duration | Files Created | Sources Processed |
|----------|----------|---------------|-------------------|
| **First run (3 sources)** | 5-10 min | 3 OKF docs | 3/3 |
| **Re-run (no changes)** | <1 min | 0 | 0/3 (all skipped) |
| **Re-run (1 changed)** | 2-3 min | 1 updated | 1/3 |
| **New source added** | 2-3 min | 1 new | 1/4 |

## 🎯 Quick Start Commands

```bash
# Clone and setup
git clone <repo-url>
cd amazon-ads-kb
pip install -r requirements.txt
claude /login   # if not already logged in

# Run first pipeline
python scripts/pipeline.py --config sources/seed-urls.json

# Verify results
ls knowledge/                    # Check files created
cat knowledge/log.md             # Review pipeline log (real entries only)
cat knowledge/index.md           # Check knowledge index

# Test re-run safety
python scripts/pipeline.py --config sources/seed-urls.json
# knowledge/ file count should be unchanged; log.md's newest entry should
# show Sources Skipped == however many sources were enabled and unchanged
```

## 🔧 Advanced Configuration

### Adding Custom Sources

Edit `sources/seed-urls.json`:
```json
{
  "seeds": [
    {
      "url": "https://your-custom-source.com/docs",
      "source_type": "official",  // or "community" or "blog"
      "description": "Your description",
      "enabled": true
    }
  ]
}
```

### Modifying Agent Behavior

Edit agent definitions in `.claude/agents/`:
- `scout.md` - Source discovery logic
- `extractor.md` - Fact extraction rules
- `validator.md` - Validation criteria
- `merger.md` - Merge strategies

### Custom Validation Rules

Edit `.claude/skills/dedup-rules.md` to modify:
- Topic matching thresholds
- Duplicate detection sensitivity
- Conflict resolution preferences

## 🤝 Contributing

This project uses Claude Code's agent system. To modify pipeline behavior:

1. **Subagent Logic**: Edit files in `.claude/agents/`
2. **Skills/Rules**: Edit files in `.claude/skills/`
3. **Orchestration**: Edit `scripts/pipeline.py`
4. **Validation**: Edit `scripts/validate-okf.js`

## 📄 License

MIT-0 License - See LICENSE file for details

## 🆘 Support

For issues with:
- **Claude Code**: Check Claude Code documentation
- **Fetching**: `fetch_content()` in `scripts/pipeline.py` (plain `requests` + BeautifulSoup, no MCP)
- **Pipeline Logic**: Review agent definitions in `.claude/agents/`

---

**Status**: Working prototype, not production-ready — see `RUN.md` for what's verified and what isn't, and the design document for known limitations.
**Last Updated**: 2026-08-16

**Quick Verification**: See `RUN.md` for a real command + real output, not just `ls knowledge/`.
