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

- **Node.js** (v16+) - For hash checking and validation scripts
- **Python** (v3.8+) - For pipeline orchestration
- **Git** - For version control
- **Claude Code** - Main orchestration platform

### Required MCP Servers

This project requires these Model Context Protocol (MCP) servers:

1. **Playwright MCP** - For web page content fetching
   ```bash
   npx -y @executeautomation/playwright-mcp-server
   ```

2. **Web Reader MCP** - For URL content extraction
   ```bash
   npx -y @modelcontextprotocol/server-web-reader
   ```

3. **Search MCP** - For source discovery (optional but recommended)

## 🚀 Setup Steps

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd amazon-ads-kb
```

### Step 2: Install Node.js Dependencies

```bash
npm install
```

### Step 3: Install MCP Servers

Install and configure the required MCP servers:

```bash
# Install Playwright MCP server
npm install -g @executeautomation/playwright-mcp-server

# Install Web Reader MCP server  
npm install -g @modelcontextprotocol/server-web-reader
```

### Step 4: Configure Claude Code Settings

Update your Claude Code settings file (usually at `~/.claude/settings.json` or project `.claude/settings.json`) to include the MCP servers:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@executeautomation/playwright-mcp-server"]
    },
    "web-reader": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-web-reader"]
    }
  }
}
```

### Step 5: Verify Setup

```bash
# Check that required files exist
ls .claude/agents/
ls .claude/skills/  
ls scripts/
ls sources/

# Test hash check script
python scripts/hash_check.py "https://example.com" "test content"
# Should return: "new"

# Test OKF validation
node scripts/validate-okf.js
```

### Step 6: Configure Seed URLs (Optional)

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

# Expected output after first run (with 3 sources):
# amazon-ads-help-center.md
# amazon-ads-api-resources.md  
# amazon-ppc-campaign-guide.md
# index.md
# log.md

# Count total files
ls knowledge/ | wc -l
# Should show: 5 (3 OKF docs + 2 system files)
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

# Should show entries for each pipeline run with:
# - Timestamp (e.g., ## [Full Pipeline Run] 2026-08-10T15:45:00Z)
# - Sources processed
# - Documents created/updated
# - Statistics (facts extracted, sources added, etc.)
# - Summary of changes
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

### MCP Servers Not Connecting

**Problem**: Pipeline fails with MCP connection errors

**Solution**: 
```bash
# Test MCP servers individually
npx @executeautomation/playwright-mcp-server --status
npx @modelcontextprotocol/server-web-reader --status

# Restart Claude Code after MCP installation
# Verify MCP configuration in settings.json
```

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
npm install

# Run first pipeline
python scripts/pipeline.py --config sources/seed-urls.json

# Verify results
ls knowledge/                    # Check files created
cat knowledge/log.md             # Review pipeline log
cat knowledge/index.md           # Check knowledge index

# Test re-run safety
python scripts/pipeline.py --config sources/seed-urls.json
ls knowledge/ | wc -l             # Should still be 5 files
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
- **MCP Servers**: Check respective MCP server documentation
- **Pipeline Logic**: Review agent definitions in `.claude/agents/`

---

**Status**: ✅ Production Ready  
**Last Updated**: 2026-08-10  
**Version**: 1.0.0

**Quick Verification**: After setup, run `ls knowledge/` and `cat knowledge/log.md` to confirm successful pipeline execution.
