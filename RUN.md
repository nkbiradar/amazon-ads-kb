# RUN.md — Quick Start for Evaluators

This guide helps you quickly understand, install, run, and verify the Amazon Ads Knowledge Acquisition System.

## 🎯 What This Project Does

Autonomous system that discovers Amazon Ads content from official docs, GitHub repos, and blogs → extracts facts → validates against existing knowledge → merges into structured OKF documents → publishes traceable knowledge base.

**Key Features:**
- Re-run safe (content hashing prevents duplicate processing)  
- Conflict resolution (official > community > blog)
- Complete provenance tracking (every fact cites source)
- Quality controlled (OKF format validation)

## 📋 Prerequisites

### Required Software
- **Python** (v3.8+) — `python --version`
- **Node.js** (v16+) — `node --version`  
- **Git** — `git --version`
- **Claude Code CLI** — Main orchestration platform

### Installation

```bash
# Clone repository
git clone <repository-url>
cd amazon-ads-kb

# Install Node.js dependencies  
npm install

# Verify setup
ls .claude/agents/    # Should show: extractor.md, merger.md, scout.md, validator.md
ls scripts/            # Should show: pipeline.py, validate-okf.js, etc.
ls sources/            # Should show: seed-urls.json, sources.json
```

## ⚙️ Configuration

### Seed Sources (Optional)
Edit `sources/seed-urls.json` to configure Amazon Ads sources:

```json
{
  "seeds": [
    {
      "url": "https://advertising.amazon.com/help",
      "source_type": "official", 
      "description": "Amazon Ads Help Center",
      "enabled": true
    }
  ]
}
```

**Source Types:**
- `official` — Amazon Ads documentation (highest confidence)
- `community` — GitHub repos, forums (medium confidence)  
- `blog` — Blog posts, tutorials (lowest confidence)

## 🚀 Running the Pipeline

### 1. Full Pipeline (Recommended First Step)

```bash
# Run complete pipeline with all seed sources
python scripts/pipeline.py --config sources/seed-urls.json
```

**What happens:**
1. Fetches content from each source URL
2. Extracts factual claims (rejects marketing fluff, JavaScript, etc.)
3. Validates facts against existing knowledge (duplicates, conflicts, new)
4. Merges into OKF documents in `knowledge/` directory
5. Updates index and logs

**Expected time:** 5-10 minutes (first run), <1 minute (re-runs with no changes)

### 2. Single Source (Testing)

```bash
# Test with one source
python scripts/pipeline.py --url "https://advertising.amazon.com/solutions/products/sponsored-products" --type official
```

### 3. Re-run Safety Verification

```bash
# Run pipeline twice to verify hash-based change detection
python scripts/pipeline.py --config sources/seed-urls.json
python scripts/pipeline.py --config sources/seed-urls.json
```

Second run should show: "Sources skipped: X" (unchanged sources)

## 📊 Expected Output

### Knowledge Directory Structure
```
knowledge/
├── index.md                           # Topic index and statistics
├── log.md                             # Pipeline execution log
├── products-sponsored-products.md      # Generated OKF document
├── amazon-dsp-demand-side-platform.md # Another OKF document
└── ...                                # More OKF documents
```

### OKF Document Format
Every generated document has:
```yaml
---
title: "Document Title"
last_updated: 2026-08-13T20:07:58Z
type: knowledge
sources:
  - url: "https://..."
    type: official
    confidence: high
topic_id: document-slug
---
```

### Fact Format
Each fact includes:
- Factual claim about Amazon Ads
- Inline citation: `[¹](https://source-url)`
- Provenance: `<!-- provenance: source_url="..." source_type="..." confidence="high" last_checked="..." -->`

## 🧪 Running Tests

### 1. OKF Validation Test
```bash
python scripts/test_okf_validation.py
```

**Expected:** All knowledge documents pass validation, N/N PASS (N = however
many `.md` files are in `knowledge/` excluding `index.md`/`log.md` — 13 after
the 2026-08-16 consolidation described in `knowledge/index.md`, until you
delete the 13 leftover files listed there, in which case it'll read 26/26)

### 2. Error-Handling Test
```bash
python okf-test-suite/run_error_handling_tests.py
```

**Expected:** 12/12 test cases pass (11 original + 1 isolating the type-field rule specifically, added 2026-08-16)

### 3. Direct Document Validation
```bash
cat knowledge/products-sponsored-products.md | python3 -c "
import json, sys
content = sys.stdin.read()
print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'knowledge/products-sponsored-products.md','content':content}}))
" | node scripts/validate-okf.js
```

**Expected:** No output (success), or validation results

## 🔍 How to Verify Results

### Quick Verification Commands
```bash
# Check knowledge documents were created
ls knowledge/

# View pipeline log
tail -30 knowledge/log.md

# Check knowledge index
cat knowledge/index.md

# Verify no JavaScript artifacts in generated content
grep -r "function(" knowledge/*.md | wc -l  # Should return 0

# Check hash tracking works
cat sources/sources.json | head -20
```

### Quality Checks
```bash
# Sample document structure check
head -20 knowledge/products-sponsored-products.md

# Verify provenance metadata
grep "provenance:" knowledge/*.md | wc -l  # Should show many results

# Check for proper citations
grep "\[¹\]" knowledge/*.md | wc -l     # Should show many results
```

## 🏗️ How It Works

### Pipeline Stages
```
Discover → Extract → Validate → Merge → Publish
```

### Agent Invocations
The pipeline uses 4 specialized Claude agents:

1. **Scout Agent** (`.claude/agents/scout.md`)
   - Discovers and verifies source URLs
   - Checks reachability and categorizes sources

2. **Extractor Agent** (`.claude/agents/extractor.md`) 
   - Extracts factual claims from content
   - Rejects marketing fluff, navigation text, JavaScript
   - Returns structured JSON with provenance

3. **Validator Agent** (`.claude/agents/validator.md`)
   - Checks facts against existing knowledge
   - Detects duplicates, conflicts, new information
   - Resolves conflicts using confidence hierarchy

4. **Merger Agent** (`.claude/agents/merger.md`)
   - Creates or updates OKF documents
   - Merges facts with proper citations
   - Updates index and change log

### Rerun/Hash Safety
- **Content Hashing**: Each source gets SHA-256 hash of content
- **Change Detection**: Only processes sources with changed hashes  
- **Idempotency**: Safe to run multiple times
- **Efficiency**: Unchanged sources skipped instantly

**Hash Storage:** `sources/sources.json`
```json
{
  "sources": {
    "https://example.com": {
      "content_hash": "abc123...",
      "last_checked": "2026-08-13T20:00:00Z",
      "last_changed": "2026-08-13T20:00:00Z",
      "source_type": "official"
    }
  }
}
```

### Provenance Tracking
Every fact includes complete provenance:

```markdown
- Sponsored Products are cost-per-click ads [¹](https://advertising.amazon.com/sp)
<!-- provenance: source_url="https://..." source_type="official" confidence="high" last_checked="2026-08-13T20:07:58Z" -->
```

**Provenance Fields:**
- `source_url` — Exact source URL
- `source_type` — official/community/blog
- `confidence` — high/medium/low
- `last_checked` — ISO timestamp of last verification

### OKF Validation
All documents validated before writing:

**Required Frontmatter:**
- `title` — Document title
- `last_updated` — ISO timestamp
- `type` — Non-empty string; the pipeline always writes `knowledge`, but `scripts/validate-okf.js` accepts any non-empty value (the OKF v0.1 rule is "present and non-empty", not a fixed enum)
- `sources` — Array of source objects
- `topic_id` — Document identifier

**Validation Hook:** Pre-write validation via `.claude/settings.json`

## 🐛 Troubleshooting

### Pipeline Runs But No Documents Created
**Check:** 
```bash
# Verify seed URLs are configured
cat sources/seed-urls.json

# Test with single known-good source
python scripts/pipeline.py --url "https://advertising.amazon.com/solutions/products/sponsored-products" --type official

# Check pipeline output for errors
python scripts/pipeline.py --config sources/seed-urls.json 2>&1 | grep -i error
```

### Sources Skipped But Should Be Processed
**Check:**
```bash
# Clear the hash entry for one URL so it's re-processed instead of skipped.
# Plain script on purpose -- no shell here-doc/quoting, so it works the same
# in PowerShell, cmd, and bash.
python scripts/reset_source.py "https://advertising.amazon.com/solutions/products/sponsored-products"

# With no URL argument it just lists tracked source URLs, no writes.
python scripts/reset_source.py
```

### Validation Fails
**Check:**
```bash
# Verify document has required frontmatter
head -15 knowledge/<problematic-file>.md

# Run validation manually for details — the hook reads a tool-invocation JSON
# from stdin, it does not take a file path argument:
python3 -c "
import json
content = open('knowledge/<problematic-file>.md', encoding='utf-8').read()
print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'knowledge/<problematic-file>.md','content':content}}))
" | node scripts/validate-okf.js; echo "exit: $?"
```

### Agent Errors
**Check:**
```bash
# Verify agent definitions exist
ls .claude/agents/

# Check that agents are being invoked
# (Agent invocation appears in pipeline output)
```

## 📈 Performance Expectations

| Scenario | Duration | New Docs | Updated Docs | Sources Skipped |
|----------|----------|-----------|---------------|-----------------|
| **First run (3 sources)** | 5-10 min | 3 | 0 | 0 |
| **Re-run (no changes)** | <1 min | 0 | 0 | All (3/3) |
| **Re-run (1 changed)** | 2-3 min | 0 | 1 | 2/3 |
| **New source added** | 2-3 min | 1 | 0 | Previous sources |

## 🎯 Evaluation Checklist

Use this checklist to verify system functionality:

- [ ] README.md clearly explains project purpose
- [ ] Prerequisites and installation instructions clear
- [ ] Pipeline runs successfully: `python scripts/pipeline.py --config sources/seed-urls.json`
- [ ] Knowledge documents created in `knowledge/` directory
- [ ] Documents have proper OKF frontmatter (title, last_updated, type, sources, topic_id)
- [ ] Facts include inline citations `[¹](url)` format
- [ ] Facts include provenance metadata (source_url, source_type, confidence, last_checked)
- [ ] No JavaScript/tracking code in facts (grep for "function(", "var ue_csm" returns 0)
- [ ] OKF validation passes: `python scripts/test_okf_validation.py` shows N/N PASS
- [ ] Error-handling tests pass: `python okf-test-suite/run_error_handling_tests.py` shows 12/12 PASS
- [ ] Direct validation works: pipe a `{"tool_name":"Write","tool_input":{...}}` JSON payload to `node scripts/validate-okf.js` (see Troubleshooting above) — exit 0 valid, exit 2 blocked
- [ ] Rerun safety verified: Second pipeline run skips unchanged sources
- [ ] Hash tracking working: `sources/sources.json` contains content_hash entries
- [ ] Index updated: `knowledge/index.md` lists all documents
- [ ] Log entries written: `knowledge/log.md` shows pipeline runs

## 🚦 Quick Evaluation Commands

Run these commands in sequence to verify complete system:

```bash
# 1. Setup check
ls .claude/agents/ scripts/ sources/

# 2. Run pipeline  
python scripts/pipeline.py --config sources/seed-urls.json

# 3. Verify results
ls knowledge/
cat knowledge/index.md
tail -20 knowledge/log.md

# 4. Test rerun safety
python scripts/pipeline.py --config sources/seed-urls.json
grep "Sources skipped" knowledge/log.md | tail -1

# 5. Run validation tests
python scripts/test_okf_validation.py
python okf-test-suite/run_error_handling_tests.py
cat knowledge/products-sponsored-products.md | python3 -c "
import json, sys
content = sys.stdin.read()
print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'knowledge/products-sponsored-products.md','content':content}}))
" | node scripts/validate-okf.js

# 6. Quality checks
grep -r "function(" knowledge/*.md | wc -l  # Should be 0
grep "provenance:" knowledge/*.md | wc -l     # Should be many

# 7. Verify clean state
git diff --check
git status --short
```

## 📚 Additional Documentation

- **README.md** — Comprehensive project documentation
- **CLAUDE.md** — Project scope and architecture
- **.claude/agents/** — Individual agent definitions
- **.claude/skills/** — Reusable skills (OKF format, deduplication, citation rules)

---

## What's actually been verified, and what you need to verify yourself

Being specific about this on purpose — a prior version of this file (and of
`knowledge/log.md`) described pipeline behavior that didn't match what the
code did. Here's what was actually run, live, with real output, and what
still needs a run on a machine with an authenticated `claude` CLI and open
network access to advertising.amazon.com (neither was available in the
environment these fixes were made in):

**Verified live, 2026-08-16:**
- `python scripts/test_okf_validation.py` — ran clean, real output: 26/26
  documents pass (including the regression tests for the `type` field).
  Before this fix it crashed with a `TypeError` on every real document,
  because PyYAML parses an unquoted `2026-08-10T15:45:00Z` as a
  `datetime.datetime`, not a `str` — `test_okf_validation.py` now handles
  both.
- `python okf-test-suite/run_error_handling_tests.py` — ran clean, real
  output: 12/12 (11 original cases + 1 new one isolating the type-field rule
  from every other rule). This suite previously hung indefinitely, because it
  called `validate-okf.js <file>` as a CLI argument while the script only
  reads stdin — fixed to send the same JSON payload Claude Code's PreToolUse
  hook actually sends.
- `echo '<Write payload without a type field>' | node scripts/validate-okf.js`
  — exit code 2, JSON denial reason printed. With the field present, exit 0,
  nothing printed. Ran both directly.
- `python scripts/pipeline.py --url "https://advertising.amazon.com/help" --type official`
  — ran in a sandbox with no outbound access to advertising.amazon.com and no
  logged-in `claude`. It retried 3x with backoff, failed cleanly, and wrote a
  real (not fabricated) entry to `knowledge/log.md`. This proved the error
  path but not the agent calls, because they never got the chance to run.
- **Same command, run for real by Nayan on 2026-08-16** (real network, real
  `claude` login): also produced `Sources failed: 1, Facts extracted: 0,
  Documents created: 0` — but for a different, now-understood reason.
  Fetched `https://advertising.amazon.com/help` directly (outside the
  pipeline) and confirmed it returns a client-side-rendered app shell: a
  tracking pixel and `title: Amazon`, no body HTML at all. `fetch_content()`
  uses plain `requests`, which can't run the JavaScript that renders that
  page's real content — so it correctly reported `empty_content` and skipped
  rather than fabricating a document. Also directly fetched
  `/help/GTEHPEG5BXY9UX5W` and `/API/docs/en-us/guides/reporting/v2/metrics`
  and got the same empty shell — this is a property of those specific URL
  patterns on this domain, not a one-off. `/library/guides/*` and
  `/solutions/products/*` URLs, fetched the same way, returned full
  server-rendered article HTML. All three broken URLs are now disabled in
  `sources/seed-urls.json` with a `note` field explaining why, and the
  README/RUN.md/CLAUDE.md examples were switched to
  `/solutions/products/sponsored-products`, which is confirmed real content.

**Verified live, 2026-08-16 (Nayan's machine, real network + real `claude` login):**
- `python scripts/pipeline.py --url "https://advertising.amazon.com/library/guides/basics-of-amazon-attribution" --type official`
  fetched real content, correctly fell back to deterministic extraction after
  the extractor agent call failed (`returncode=1` after ~6 min — see "Known
  open issue" below), extracted 8 real facts, fell back to deterministic
  validation after the merger agent call failed the same way, then crashed
  with `Error processing ...: 'last_checked'` and wrote `Documents created: 0`
  despite having 8 valid facts in hand. Root-caused to a real bug (not agent
  flakiness): `_fallback_validation` copied `fact`/`source_url`/`source_type`/
  `confidence` into its result but silently dropped `last_checked`, and
  `_create_document` then read `fact['last_checked']` via unsafe bracket
  indexing instead of `.get()` (the sibling function `_update_document`
  already used `.get()` — this one didn't). Fixed both spots, plus stamped
  `last_checked` on agent-produced facts too (the extractor agent's
  `json_schema` never requested that field, so even a successful agent call
  would have hit the same crash). Reproduced the exact failing sequence
  (fallback extraction → fallback validation → `_create_document`) in
  isolation afterward and confirmed it now completes and writes a valid OKF
  document with `last_checked` present in the provenance comment.
- Real log entries from that run are in `knowledge/log.md`
  (`## Pipeline Run: 2026-08-16T20:16:18Z`, 374.51s, `Facts extracted: 8`,
  `Documents created: 0`) — left in place rather than deleted, since the
  point of this file is to log what actually happened, crash included.

**Real end-to-end run, completed successfully, 2026-08-16T20:34:03Z (Nayan's
machine, real network, real `claude` login):**
```
python scripts/pipeline.py --url "https://advertising.amazon.com/library/guides/basics-of-amazon-attribution" --type official
```
- Extractor agent call failed (`returncode=1`) — now known why (see below) —
  fell back to deterministic extraction, found 8 real facts.
- Validator never attempted an agent call this run: `invoke_validator_agent`
  only calls the agent for batches of 5 facts or fewer (line ~872); 8 facts
  went straight to `_fallback_validation` by design. Worth noting as a real
  limitation, not glossing over it: on this run's fact count, the validator
  agent path was never exercised at all.
- Merger agent call failed (`returncode=1`, same auth error), fell back to
  deterministic merging.
- **Result: `Sources failed: 0`, `Facts extracted: 8`, `Documents created: 2`,
  no crash.** `knowledge/basics-of-amazon-attribution.md` was created with 8
  real, cited, provenance-tagged facts and passes
  `test_okf_validation.py`. Real log entry:
  `## Pipeline Run: 2026-08-16T20:34:03Z` in `knowledge/log.md`
  (362.32s, `Documents created: 2`, `Documents updated: 0`).
- The improved error logging (see below) also caught a **second real bug**
  while diagnosing this run: `documents_created`/`documents_updated` were
  being incremented twice — once inside `_execute_merger_operations`/
  `_fallback_merger`, and again by their caller aggregating the same counts
  from the returned report. That's why the summary said `Documents created: 2`
  for the single document actually written. Fixed by removing the inner
  increments; verified with a standalone repro (`_execute_merger_operations`
  now leaves `self.stats` untouched, only the caller's aggregation moves it,
  confirmed 1 real doc → stats reports 1). Re-ran `test_okf_validation.py`
  (14/14, including the new real document) and
  `run_error_handling_tests.py` (12/12) after the fix — clean.

**Agent call failure — root cause now known (not a pipeline bug):**
```
Error invoking agent: returncode=1
Agent error result: Failed to authenticate. API Error: 401 Authentication
Error, Invalid proxy server token passed. Received API Key = sk-...,
Unable to find token in cache or 'LiteLLM_VerificationTokenTable'
```
The `litellm.retap.ai` proxy token used to route the `claude` CLI to a
non-Anthropic model is invalid/expired in that environment. This surfaced
only after fixing `_invoke_claude_agent`'s error logging, which previously
truncated `result.stdout` to 500 characters — entirely consumed by envelope
metadata (`is_error`, `stop_reason`, `usage`, etc.) before ever reaching the
`"result"` field with the actual error text. The pipeline's fallback design
did exactly what it's supposed to do here: neither agent call crashed the
run, and the deterministic path produced a real, valid document instead.
Refreshing that proxy token (out of scope for this repo) would let the real
extractor/validator/merger agent calls run instead of falling back.

**Still open:**
- A transcript proving the PreToolUse hook fires inside an actual Claude Code
  session (not just the validator script run directly) — e.g. ask Claude Code
  to write a `knowledge/*.md` file missing `type` and confirm it's blocked.
- Re-run safety on a real second run (`Sources Skipped` > 0, no new files) —
  straightforward to get: run the exact same `--url` command again without
  clearing the hash first, and confirm it skips.
- A run where the extractor/merger agents actually succeed end-to-end
  (requires a valid proxy token, or running against a direct Anthropic API
  key instead of the litellm proxy).

---

**For detailed documentation:** See README.md  
**For project architecture:** See CLAUDE.md  
**For agent specifications:** See `.claude/agents/*.md`